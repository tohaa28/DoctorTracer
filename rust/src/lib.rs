// SPDX-License-Identifier: MIT
// In-memory RGBA tracing. No filesystem, network, JS bindings or C/C++ runtime.
use std::{cell::RefCell, collections::BTreeMap, fmt::Write};
use visioncortex::{color_clusters::{Runner, RunnerConfig, KeyingAction, HIERARCHICAL_MAX},
    Color, ColorImage, PathSimplifyMode, PointF64};

thread_local! { static RESULT: RefCell<Vec<u8>> = const { RefCell::new(Vec::new()) }; }

#[cfg(target_arch="wasm32")]
#[link(wasm_import_module="env")]
extern "C" {fn progress(value:u32,stage:u32);}
fn report(value:u32,stage:u32){#[cfg(target_arch="wasm32")] unsafe{progress(value,stage)} #[cfg(not(target_arch="wasm32"))] let _=(value,stage);}

// Integer edge-preserving filter; web/gpu.js uses the same arithmetic.
fn filter(pixels:&[u8],w:usize,h:usize,detail:usize)->Vec<u8>{
 let mut out=pixels.to_vec();let limit=[60i32,48,36][detail];
 for y in 0..h {for x in 0..w {
  let i=4*(y*w+x);if pixels[i+3]<128 {continue;}
  let mut sum=[0u32;3];let mut weights=0u32;
  for dy in -2i32..=2 {for dx in -2i32..=2 {
   let xx=x as i32+dx;let yy=y as i32+dy;
   if xx<0||xx>=w as i32||yy<0||yy>=h as i32 {continue;}
   let j=4*(yy as usize*w+xx as usize);if pixels[j+3]<128 {continue;}
   let diff=(0..3).map(|c|(pixels[i+c] as i32-pixels[j+c] as i32).abs()).sum::<i32>();
   let weight=((limit-diff).max(0)*(3-dx.abs())*(3-dy.abs())) as u32;
   weights+=weight;for c in 0..3 {sum[c]+=weight*pixels[j+c] as u32;}
  }}
  for c in 0..3 {out[i+c]=((sum[c]+weights/2)/weights) as u8;}
 }}out
}

#[no_mangle]
pub extern "C" fn alloc(length: usize) -> *mut u8 {
    if length > 32_000_000 { return std::ptr::null_mut(); }
    Box::into_raw(vec![0u8; length].into_boxed_slice()) as *mut u8
}
#[no_mangle]
pub unsafe extern "C" fn dealloc(ptr: *mut u8, length: usize) {
    if !ptr.is_null() { drop(Box::from_raw(std::ptr::slice_from_raw_parts_mut(ptr, length))); }
}
#[no_mangle]
pub extern "C" fn result_len() -> usize { RESULT.with(|r| r.borrow().len()) }

#[no_mangle]
pub unsafe extern "C" fn filter_rgba(ptr:*const u8,w:usize,h:usize,detail:usize)->*const u8 {
    RESULT.with(|r|r.borrow_mut().clear());
    let Some(size)=w.checked_mul(h).and_then(|n|n.checked_mul(4)) else{return std::ptr::null();};
    if ptr.is_null()||w==0||h==0||w>4096||h>4096||size>32_000_000||detail>2{return std::ptr::null();}
    let output=filter(std::slice::from_raw_parts(ptr,size),w,h,detail);
    RESULT.with(|r|{*r.borrow_mut()=output;r.borrow().as_ptr()})
}

fn distance(a: &[f64;3], b: &[f64;3]) -> f64 {
    // Green-weighted RGB distance: deterministic and inexpensive in WASM.
    (a[0]-b[0]).powi(2)*2.0+(a[1]-b[1]).powi(2)*4.0+(a[2]-b[2]).powi(2)*3.0
}

fn quantize(pixels: &mut [u8], colors: usize) -> Vec<[f64;3]> {
    let mut count=vec![0u32;32768]; let mut sums=vec![[0.;3];32768];
    for p in pixels.chunks_exact(4).filter(|p|p[3]>=128) {
        let k=((p[0] as usize>>3)<<10)|((p[1] as usize>>3)<<5)|(p[2] as usize>>3);
        count[k]+=1; for c in 0..3 {sums[k][c]+=p[c] as f64;}
    }
    let bins:Vec<usize>=(0..32768).filter(|&k|count[k]>0).collect();
    if bins.is_empty(){return Vec::new();}
    for &k in &bins {for c in 0..3 {sums[k][c]/=count[k] as f64;}}
    let first=*bins.iter().max_by_key(|&&k|count[k]).unwrap();
    let mut palette=vec![sums[first]]; let mut nearest=vec![f64::MAX;bins.len()];
    while palette.len()<colors.min(bins.len()) {
        let last=palette.last().unwrap(); let mut best=-1.;let mut chosen=first;
        for (j,&k) in bins.iter().enumerate(){nearest[j]=nearest[j].min(distance(&sums[k],last));
            let score=nearest[j]*(count[k] as f64).sqrt();if score>best {best=score;chosen=k;}}
        if best<0.01 {break;} palette.push(sums[chosen]);
    }
    let mut assignment=vec![0usize;32768];
    for _ in 0..12 {
        let mut acc=vec![[0.;3];palette.len()];let mut weights=vec![0u32;palette.len()];
        for &k in &bins {
            let label=(0..palette.len()).min_by(|&a,&b|distance(&sums[k],&palette[a]).total_cmp(&distance(&sums[k],&palette[b]))).unwrap();
            assignment[k]=label;weights[label]+=count[k];
            for c in 0..3 {acc[label][c]+=sums[k][c]*count[k] as f64;}
        }
        let mut movement=0.;for k in 0..palette.len(){if weights[k]>0 {
            for c in 0..3 {acc[k][c]/=weights[k] as f64;}
            movement+=distance(&acc[k],&palette[k]);palette[k]=acc[k];}}
        if movement<0.1 {break;}
    }
    // Reassign after the final centroid update; one lookup per histogram bin.
    for &k in &bins {assignment[k]=(0..palette.len()).min_by(|&a,&b|distance(&sums[k],&palette[a]).total_cmp(&distance(&sums[k],&palette[b]))).unwrap();}
    for p in pixels.chunks_exact_mut(4).filter(|p|p[3]>=128) {
        let k=((p[0] as usize>>3)<<10)|((p[1] as usize>>3)<<5)|(p[2] as usize>>3);
        for c in 0..3 {p[c]=palette[assignment[k]][c].round() as u8;}
    }
    palette
}

pub fn trace_image(mut pixels:Vec<u8>,w:usize,h:usize,colors:usize,detail:usize,speckle:usize,flags:u32)->Result<String,String>{
    if w==0||h==0||w>4096||h>4096||w.checked_mul(h).unwrap_or(usize::MAX)>8_000_000||pixels.len()!=w*h*4||colors==1||colors>128||detail>2||speckle>100 {return Err("Invalid trace parameters".into());}
    if !pixels.chunks_exact(4).any(|p|p[3]>=128){report(100,6);return Ok(format!("<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"{w}\" height=\"{h}\" viewBox=\"0 0 {w} {h}\"><g id=\"image\"/></svg>"));}
    report(8,1);
    if flags&6==0 {pixels=filter(&pixels,w,h,detail);}
    report(20,2);
    let palette=if colors>0 {quantize(&mut pixels,colors)}else{Vec::new()};
    report(42,3);
    // A deterministic unused colour keys EVERY transparent pixel, including tiny holes.
    // VTracer's scanline heuristic otherwise misses small interior transparent regions.
    let mut used=vec![false;1<<24];
    for p in pixels.chunks_exact(4).filter(|p|p[3]>=128){used[((p[0] as usize)<<16)|((p[1] as usize)<<8)|p[2] as usize]=true;}
    let key=used.iter().position(|&v|!v).ok_or("No transparency key available")?;
    drop(used);let key_color=Color::new((key>>16) as u8,(key>>8) as u8,key as u8);
    for p in pixels.chunks_exact_mut(4){if p[3]<128 {p.copy_from_slice(&[key_color.r,key_color.g,key_color.b,255]);}else{p[3]=255;}}
    let transparent:Vec<bool>=pixels.chunks_exact(4).map(|p|p[0]==key_color.r&&p[1]==key_color.g&&p[2]==key_color.b).collect();
    let runner=Runner::new(RunnerConfig {diagonal:false,hierarchical:HIERARCHICAL_MAX,batch_size:25600,
        good_min_area:speckle,good_max_area:w*h,is_same_color_a:0,is_same_color_b:1,
        deepen_diff:if colors>0 {0}else{[40,24,12][detail]},hollow_neighbours:1,
        key_color,keying_action:KeyingAction::Keep},ColorImage{pixels,width:w,height:h});
    let clusters=runner.run();report(62,4);let mut image=clusters.view().to_color_image();
    for (i,&clear) in transparent.iter().enumerate(){if clear {image.pixels[4*i..4*i+4].copy_from_slice(&[key_color.r,key_color.g,key_color.b,255]);}}
    // Cutout pass: disjoint region masks, rather than a full-image underpainting.
    let clusters=Runner::new(RunnerConfig {diagonal:false,hierarchical:64,batch_size:25600,
        good_min_area:0,good_max_area:w*h,is_same_color_a:0,is_same_color_b:1,deepen_diff:0,
        hollow_neighbours:0,key_color,keying_action:KeyingAction::Discard},image).run();
    let view=clusters.view();let mut groups:BTreeMap<String,Vec<String>>=BTreeMap::new();
    for (i,&idx) in view.clusters_output.iter().rev().enumerate(){
        if i%20==0 {report(70+(25*i/view.clusters_output.len().max(1)) as u32,5);}
        let cluster=view.get_cluster(idx);
        let paths=cluster.to_compound_path(&view,true,if cluster.area()<4 {PathSimplifyMode::None}else if flags&1!=0 {PathSimplifyMode::Polygon}else{PathSimplifyMode::Spline},
            60f64.to_radians(),[6.,4.,2.][detail],10,45f64.to_radians());
        let (mut data,offset)=paths.to_svg_string(true,PointF64::default(),Some(3));
        // The spline fitter drops one-pixel holes; preserve them as exact
        // reverse-wound unit rectangles within the SAME editable curve.
        let binary=cluster.to_image_with_hole(view.width,true);
        for hole in binary.negative().to_clusters(false).iter(){
            if hole.size()==1 && hole.rect.left>0 && hole.rect.top>0 && hole.rect.right<(binary.width as i32) && hole.rect.bottom<(binary.height as i32){
                let x=cluster.rect.left as f64+hole.rect.left as f64-offset.x;
                let y=cluster.rect.top as f64+hole.rect.top as f64-offset.y;
                write!(data," M{x} {y} L{x} {} L{} {} L{} {y} Z",y+1.,x+1.,y+1.,x+1.).unwrap();
            }
        }
        let residue=cluster.residue_color();
        let color=if palette.is_empty(){residue}else{
            let rgb=[residue.r as f64,residue.g as f64,residue.b as f64];
            let nearest=palette.iter().min_by(|a,b|distance(a,&rgb).total_cmp(&distance(b,&rgb))).unwrap();
            Color::new(nearest[0].round() as u8,nearest[1].round() as u8,nearest[2].round() as u8)
        };
        if !data.is_empty(){groups.entry(color.to_hex_string()).or_default().push(format!("<path d=\"{data}\" transform=\"translate({},{})\"/>",offset.x,offset.y));}
    }
    let mut svg=format!("<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"{w}\" height=\"{h}\" viewBox=\"0 0 {w} {h}\"><g id=\"image\">");
    for (color,paths) in groups {write!(svg,"<g id=\"color-{}\" fill=\"{color}\" fill-rule=\"nonzero\">{}</g>",color.trim_start_matches('#'),paths.join("")).unwrap();}
    svg.push_str("</g></svg>");report(100,6);Ok(svg)
}

#[no_mangle]
pub unsafe extern "C" fn trace_rgba(ptr:*const u8,w:usize,h:usize,colors:usize,detail:usize,speckle:usize,polygon:u32)->*const u8 {
    RESULT.with(|r|r.borrow_mut().clear());
    let Some(size)=w.checked_mul(h).and_then(|n|n.checked_mul(4)) else{return std::ptr::null();};
    if ptr.is_null()||size>32_000_000||w==0||h==0 {return std::ptr::null();}
    match trace_image(std::slice::from_raw_parts(ptr,size).to_vec(),w,h,colors,detail,speckle,polygon){
        Ok(svg)=>RESULT.with(|r|{*r.borrow_mut()=svg.into_bytes();r.borrow().as_ptr()}),
        Err(_)=>std::ptr::null()
    }
}
