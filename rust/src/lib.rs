// SPDX-License-Identifier: MIT
// Desktop photographic algorithm port. Pixels remain in a dedicated Web Worker.
mod post_smooth;mod shared_contract;mod joint_palette;mod raster_refit;mod edge_fit;mod desktop_filters;mod desktop_palette;mod desktop_regions;mod desktop_shared;
use std::cell::RefCell;
thread_local!{static RESULT:RefCell<Vec<u8>>=const{RefCell::new(Vec::new())};static PALETTE:RefCell<Vec<[u8;3]>>=const{RefCell::new(Vec::new())};static STATS:RefCell<Vec<u8>>=const{RefCell::new(Vec::new())};static SEGMENT:RefCell<Vec<u8>>=const{RefCell::new(Vec::new())};static LAST:RefCell<Option<(Vec<i32>,Vec<[u8;3]>,usize,usize,usize)>>=const{RefCell::new(None)};}
#[cfg(target_arch="wasm32")]#[link(wasm_import_module="env")]extern "C"{fn progress(value:u32,stage:u32);}
fn report(value:u32,stage:u32){#[cfg(target_arch="wasm32")]unsafe{progress(value,stage)}#[cfg(not(target_arch="wasm32"))]let _=(value,stage);}
fn store(bytes:Vec<u8>)->*const u8{RESULT.with(|r|{*r.borrow_mut()=bytes;r.borrow().as_ptr()})}
fn valid(w:usize,h:usize)->bool{w>0&&h>0&&w<=4096&&h<=4096&&w.checked_mul(h).unwrap_or(usize::MAX)<=8_000_000}
#[no_mangle]pub extern "C" fn alloc(n:usize)->*mut u8{if n>128_000_000{return std::ptr::null_mut();}Box::into_raw(vec![0u8;n].into_boxed_slice()) as *mut u8}
#[no_mangle]pub unsafe extern "C" fn dealloc(p:*mut u8,n:usize){if !p.is_null(){drop(Box::from_raw(std::ptr::slice_from_raw_parts_mut(p,n)));}}
#[no_mangle]pub extern "C" fn result_len()->usize{RESULT.with(|r|r.borrow().len())}
#[no_mangle]pub extern "C" fn stats_ptr()->*const u8{STATS.with(|r|r.borrow().as_ptr())}
#[no_mangle]pub extern "C" fn stats_len()->usize{STATS.with(|r|r.borrow().len())}
#[no_mangle]pub unsafe extern "C" fn set_palette(p:*const u8,k:usize){PALETTE.with(|r|{let mut pal=r.borrow_mut();pal.clear();if k>0&&k<=128&&!p.is_null(){for color in std::slice::from_raw_parts(p,k*3).chunks_exact(3){pal.push([color[0],color[1],color[2]]);}}});}
#[no_mangle]pub unsafe extern "C" fn filter_rgba(p:*const u8,w:usize,h:usize,_detail:usize)->*const u8{if p.is_null()||!valid(w,h){return std::ptr::null();}store(desktop_filters::bilateral(std::slice::from_raw_parts(p,w*h*4),w,h))}
#[no_mangle]pub unsafe extern "C" fn desktop_stage(p:*const u8,w:usize,h:usize,colors:usize,detail:usize,kind:usize,extra:usize)->*const u8{
 if p.is_null()||!valid(w,h)||detail>2||colors>128{return std::ptr::null();}let a=std::slice::from_raw_parts(p,w*h*4);
 let output=match kind{0=>desktop_filters::bilateral(a,w,h),1=>desktop_filters::modes(a,w,h,detail),2=>desktop_palette::find(a,w,h,colors,extra!=0).into_iter().flatten().collect(),3=>{let pal=PALETTE.with(|r|r.borrow().clone());if pal.is_empty(){return std::ptr::null();}desktop_filters::segment(a,w,h,&pal,(extra&65535) as i32,extra&65536!=0,if extra>>17==0{3}else{extra>>17})},4=>{let mut labels=a[..w*h].to_vec();let pal=PALETTE.with(|r|r.borrow().clone());if pal.len()==colors{desktop_filters::clean_aware(&mut labels,w,h,&pal,extra&65535,extra>>16);}else{desktop_filters::clean(&mut labels,w,h,colors,extra&65535,extra>>16);}labels},6=>desktop_filters::resize2(a,w,h),_=>return std::ptr::null()};store(output)
}
#[no_mangle]pub unsafe extern "C" fn shared_svg(p:*const i32,w:usize,h:usize,detail:usize,flags:usize)->*const u8{if p.is_null()||!valid(w,h)||detail>2{return std::ptr::null();}let pal=PALETTE.with(|r|r.borrow().clone());let labels=std::slice::from_raw_parts(p,w*h);if labels.iter().any(|&v|v>=pal.len() as i32){return std::ptr::null();}store(desktop_shared::trace(labels,&pal,w,h,detail,flags&1!=0,flags&2!=0,flags&4!=0).into_bytes())}
#[no_mangle]pub extern "C" fn segment_preview()->*const u8{store(SEGMENT.with(|r|r.borrow().clone()))}
#[no_mangle]pub extern "C" fn shared_fallback()->*const u8{LAST.with(|r|if let Some((labels,palette,w,h,detail))=&*r.borrow(){store(desktop_shared::trace(labels,palette,*w,*h,*detail,false,false,false).into_bytes())}else{std::ptr::null()})}
#[no_mangle]pub unsafe extern "C" fn trace_rgba(p:*const u8,w:usize,h:usize,colors:usize,detail:usize,speckle:usize,flags:usize)->*const u8{
 RESULT.with(|r|r.borrow_mut().clear());if p.is_null()||!valid(w,h)||colors==1||colors>128||detail>2||speckle>100{return std::ptr::null();}
 let mut a=std::slice::from_raw_parts(p,w*h*4).to_vec();let photo=flags&12==0;let manual=PALETTE.with(|r|r.borrow().clone());let flags=if manual.is_empty()&&colors>0{flags|2048}else{flags};let unlimited=photo&&colors==0&&manual.is_empty();report(3,1);
 if flags&2==0{if photo||detail==0||flags&16!=0{a=desktop_filters::bilateral(&a,w,h);}if unlimited{report(8,1);a=desktop_filters::modes(&a,w,h,detail);}}
 report(18,2);let palette=if manual.is_empty(){desktop_palette::find(&a,w,h,if unlimited{64}else{colors},photo)}else{manual};
 report(28,3);let labels=desktop_filters::segment(&a,w,h,&palette,if photo{if unlimited{200}else{700}}else{0},flags&8!=0&&palette.len()<=24,3);
 store(finish(a,labels,palette,w,h,unlimited,detail,speckle,flags).into_bytes())
}

thread_local!{static EDGE_SOURCE:std::cell::RefCell<Vec<u8>>=std::cell::RefCell::new(Vec::new());}
fn finish(a:Vec<u8>,mut labels:Vec<u8>,mut palette:Vec<[u8;3]>,w:usize,h:usize,unlimited:bool,detail:usize,speckle:usize,flags:usize)->String{
 let photo=flags&12==0;
 if flags&4096==0{if unlimited{desktop_filters::clean(&mut labels,w,h,palette.len(),speckle.max(8),(flags>>8)&3);}else{desktop_filters::clean_aware(&mut labels,w,h,&palette,if photo{speckle.max(8)}else{speckle.max(1)},(flags>>8)&3);}}
 if !unlimited && photo && flags&2048!=0{crate::joint_palette::refine(&a,&mut labels,&mut palette,w,h);}
 SEGMENT.with(|r|{let mut rgba=vec![0u8;w*h*4];for(i,&label)in labels.iter().enumerate(){if label!=255{rgba[4*i..4*i+3].copy_from_slice(&palette[label as usize]);rgba[4*i+3]=255;}}*r.borrow_mut()=rgba;});
 report(40,4);let(mut regions,mut inks)=if unlimited{desktop_regions::components(&labels,&a,w,h,palette.len())}else{(labels.iter().map(|&v|if v==255{-1}else{v as i32}).collect(),palette.clone())};
 let initial=inks.len();let target=if unlimited{desktop_regions::target(&labels,&a,w,h,detail)}else{inks.len()};report(60,4);if unlimited{desktop_regions::merge(&mut regions,&mut inks,w,h,target);}
 EDGE_SOURCE.with(|r|*r.borrow_mut()=a.clone());
 REFIT_INFO.with(|r|*r.borrow_mut()=b"{}".to_vec());RASTER_BASE.with(|r|r.borrow_mut().clear());
 report(70,5);let svg=if flags&128!=0{String::new()}else{desktop_shared::trace_quality(&regions,&inks,w,h,detail,flags&32==0,flags&1!=0,!unlimited,None,Some(&a))};
 let svg=if !svg.is_empty()&&flags&32==0&&photo{raster_pass(svg,&a,w,h)}else{svg};
 LAST.with(|r|*r.borrow_mut()=Some((regions,inks.clone(),w,h,detail)));
 let palette_json=palette.iter().map(|p|format!("[{}, {}, {}]",p[0],p[1],p[2])).collect::<Vec<_>>().join(",");let refit=REFIT_INFO.with(|r|String::from_utf8_lossy(&r.borrow()).into_owned());let stats=format!("{{\"raster_refit\":{refit},\"algorithm\":\"desktop-shared\",\"initial_regions\":{initial},\"region_target\":{target},\"regions\":{},\"palette\":[{palette_json}]}}",inks.len());STATS.with(|r|*r.borrow_mut()=stats.into_bytes());report(100,6);svg
}

#[no_mangle]pub unsafe extern "C" fn trace_labels(p:*const u8,l:*const u8,w:usize,h:usize,detail:usize,speckle:usize,flags:usize,unlimited:usize)->*const u8{
 if p.is_null()||l.is_null()||!valid(w,h)||detail>2||speckle>100{return std::ptr::null();}let palette=PALETTE.with(|r|r.borrow().clone());let labels=std::slice::from_raw_parts(l,w*h).to_vec();if palette.is_empty()||labels.iter().any(|&v|v!=255&&v as usize>=palette.len()){return std::ptr::null();}let a=std::slice::from_raw_parts(p,w*h*4).to_vec();store(finish(a,labels,palette,w,h,unlimited!=0,detail,speckle,flags).into_bytes())
}

#[no_mangle]pub unsafe extern "C" fn analyze_rgba(p:*const u8,w:usize,h:usize)->*const u8{
 if p.is_null()||!valid(w,h){return std::ptr::null();}let a=std::slice::from_raw_parts(p,w*h*4);let palette=desktop_palette::find(a,w,h,0,false);let visible:Vec<_>=a.chunks_exact(4).filter(|p|p[3]>=128).collect();let samples:Vec<_>=if visible.is_empty(){vec![&a[..4]]}else{visible.iter().step_by((visible.len()/30000).max(1)).copied().collect()};let matches=samples.iter().filter(|p|palette.iter().any(|color|(0..3).map(|c|(p[c] as i32-color[c] as i32).pow(2)).sum::<i32>()<1225)).count();let coverage=matches as f64/samples.len() as f64;let category=if coverage<0.8||palette.len()>18{"photo"}else{"aa"};let list=palette.iter().map(|p|format!("[{}, {}, {}]",p[0],p[1],p[2])).collect::<Vec<_>>().join(",");store(format!("{{\"category\":\"{category}\",\"coverage\":{coverage},\"palette\":[{list}]}}").into_bytes())
}

// Deferred shared geometry lets WebGPU compute the same dyadic vertex coordinates.
#[no_mangle]pub extern "C" fn shared_input()->*const u8{LAST.with(|r|if let Some((labels,palette,_,_,_))=&*r.borrow(){store(labels.iter().flat_map(|&v|{let value=if v<0{-1}else{let p=palette[v as usize];p[0] as i32|((p[1] as i32)<<8)|((p[2] as i32)<<16)};value.to_le_bytes()}).collect())}else{std::ptr::null()})}
#[no_mangle]pub unsafe extern "C" fn shared_finish(p:*const u32,length:usize,passes:usize,flags:usize)->*const u8{
 LAST.with(|r|if let Some((labels,palette,w,h,detail))=&*r.borrow(){
  let fixed=flags&4!=0;let expected=if fixed{[4,2,1][*detail]}else{[10,8,5][*detail]};
  if !p.is_null()&&(passes!=expected||length!=2*(w+1)*(h+1)){return std::ptr::null();}
  let external=if p.is_null(){None}else{Some((std::slice::from_raw_parts(p,2*(w+1)*(h+1)),1u32<<(2*passes)))};
  EDGE_SOURCE.with(|source|{let source=source.borrow();let svg=desktop_shared::trace_quality(labels,palette,*w,*h,*detail,flags&1!=0,flags&2!=0,fixed,external,if source.len()==w*h*4{Some(&source)}else{None});let svg=if flags&1!=0&&source.len()==w*h*4{raster_pass(svg,&source,*w,*h)}else{svg};let info=REFIT_INFO.with(|r|String::from_utf8_lossy(&r.borrow()).into_owned());STATS.with(|r|{let text=String::from_utf8_lossy(&r.borrow()).replace("\"raster_refit\":{}",&format!("\"raster_refit\":{info}"));*r.borrow_mut()=text.into_bytes();});store(svg.into_bytes())})
 }else{std::ptr::null()})
}

thread_local!{static REFIT_INFO:RefCell<Vec<u8>>=RefCell::new(Vec::new());}
#[no_mangle]pub unsafe extern "C" fn raster_refit(p:*const u8,length:usize,a:*const u8,w:usize,h:usize)->*const u8{
 if p.is_null()||a.is_null()||!valid(w,h)||length>32_000_000{return std::ptr::null();}let Ok(svg)=std::str::from_utf8(std::slice::from_raw_parts(p,length))else{return std::ptr::null();};let source=std::slice::from_raw_parts(a,w*h*4);let(result,before,after,tension)=raster_refit::refit(svg,source,w,h);REFIT_INFO.with(|r|*r.borrow_mut()=format!("{{\"before\":{before},\"after\":{after},\"tension\":{tension},\"renderer\":\"independent scanline adaptive 4x/2x\"}}").into_bytes());store(result.into_bytes())
}
#[no_mangle]pub extern "C" fn raster_refit_info()->*const u8{store(REFIT_INFO.with(|r|r.borrow().clone()))}

thread_local!{static RASTER_BASE:RefCell<Vec<u8>>=RefCell::new(Vec::new());}
#[no_mangle]pub extern "C" fn raster_base()->*const u8{store(RASTER_BASE.with(|r|r.borrow().clone()))}
fn raster_pass(svg:String,a:&[u8],w:usize,h:usize)->String{
 RASTER_BASE.with(|r|*r.borrow_mut()=svg.as_bytes().to_vec());let(result,before,after,tension)=raster_refit::refit(&svg,a,w,h);REFIT_INFO.with(|r|*r.borrow_mut()=format!("{{\"before\":{before},\"after\":{after},\"tension\":{tension}}}").into_bytes());result
}

#[no_mangle]pub unsafe extern "C" fn joint_proposal(p:*const u8,l:*const u8,w:usize,h:usize)->*const u8{
 if p.is_null()||l.is_null()||!valid(w,h){return std::ptr::null();}let a=std::slice::from_raw_parts(p,w*h*4);let labels=std::slice::from_raw_parts(l,w*h);let pal=PALETTE.with(|r|r.borrow().clone());if pal.is_empty()||labels.iter().enumerate().any(|(i,&v)|a[4*i+3]>=128&&v as usize>=pal.len()){return std::ptr::null();}store(joint_palette::propose(a,labels,&pal,w,h).into_iter().flatten().collect())
}
#[no_mangle]pub unsafe extern "C" fn joint_choose(p:*const u8,l:*const u8,c:*const u8,w:usize,h:usize)->*const u8{
 if p.is_null()||l.is_null()||c.is_null()||!valid(w,h){return std::ptr::null();}let a=std::slice::from_raw_parts(p,w*h*4);let old=std::slice::from_raw_parts(l,w*h);let candidate=std::slice::from_raw_parts(c,w*h);let pal=PALETTE.with(|r|r.borrow().clone());if pal.is_empty()||old.iter().chain(candidate).any(|&v|v!=255&&v as usize>=pal.len())||old.iter().zip(candidate).enumerate().any(|(i,(&u,&v))|a[4*i+3]>=128&&(u==255||v==255)){return std::ptr::null();}store(joint_palette::choose(a,old,candidate,&pal,w,h))
}

#[no_mangle]pub unsafe extern "C" fn result_smooth(p:*const u8,n:usize,strength:u32,sharp:u32)->*const u8{
 if p.is_null()||n>32_000_000{return std::ptr::null();}
 let Ok(svg)=std::str::from_utf8(std::slice::from_raw_parts(p,n))else{return std::ptr::null();};
 match post_smooth::smooth(svg,strength,sharp!=0){
  Ok((out,nodes,moved))=>{STATS.with(|r|*r.borrow_mut()=format!("{{\"nodes\":{nodes},\"moved\":{moved}}}").into_bytes());store(out.into_bytes())},
  Err(_)=>{STATS.with(|r|*r.borrow_mut()=b"{\"error\":\"Unsafe or unsupported geometry\"}".to_vec());std::ptr::null()}
 }
}
