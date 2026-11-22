// Standalone smoothing of finished SVG geometry. No raster or palette changes.
use std::collections::HashMap;
use std::fmt::Write;
type P=[f64;2];
#[derive(Clone)]struct Edge{a:usize,b:usize,c:Option<[P;2]>,uses:Vec<bool>}
enum Cmd{M(usize),E(usize,bool),Z}
struct Path{tag:String,d:String,cmd:Vec<Cmd>}
fn attr<'a>(s:&'a str,k:&str)->Option<&'a str>{let n=format!("{k}=\"");let i=s.match_indices(&n).find(|(i,_)|*i>0&&s.as_bytes()[i-1].is_ascii_whitespace())?.0+n.len();let r=&s[i..];Some(&r[..r.find('"')?])}
fn node(p:P,nodes:&mut Vec<P>,map:&mut HashMap<[i64;2],usize>)->usize{let q=p.map(|v|(v*1e6).round() as i64);*map.entry(q).or_insert_with(||{nodes.push(q.map(|v|v as f64/1e6));nodes.len()-1})}
fn add(a:usize,b:usize,c:Option<[P;2]>,nodes:&[P],edges:&mut Vec<Edge>,map:&mut HashMap<Vec<i64>,usize>)->(usize,bool){
 let mut f=vec![if c.is_some(){1}else{0}];f.extend(nodes[a].map(|v|(v*1e6).round() as i64));if let Some(cs)=c{for p in cs{f.extend(p.map(|v|(v*1e6).round() as i64));}}f.extend(nodes[b].map(|v|(v*1e6).round() as i64));
 let mut r=vec![f[0]];for pair in f[1..].chunks_exact(2).rev(){r.extend(pair);}let rev=f>r;let key=if rev{r}else{f};
 let id=*map.entry(key).or_insert_with(||{edges.push(if rev{Edge{a:b,b:a,c:c.map(|v|[v[1],v[0]]),uses:Vec::new()}}else{Edge{a,b,c,uses:Vec::new()}});edges.len()-1});edges[id].uses.push(rev);(id,rev)
}
fn area(ids:&[usize],p:&[P])->f64{ids.iter().enumerate().map(|(i,&a)|{let b=ids[(i+1)%ids.len()];p[a][0]*p[b][1]-p[b][0]*p[a][1]}).sum::<f64>()*0.5}
fn clamp(p:P,original:P,max:f64)->P{let d=[p[0]-original[0],p[1]-original[1]];let n=d[0].hypot(d[1]);let s=if n>max{max/n}else{1.};[original[0]+d[0]*s,original[1]+d[1]*s]}
pub fn smooth(svg:&str,strength:u32,sharp:bool)->Result<(String,usize,usize),&'static str>{
 if svg.len()>32_000_000{return Err("SVG is too large");}if svg.contains("transform="){return Err("Transformed paths are not supported");}
 let strength=strength.min(100);if strength==0{return Ok((svg.to_string(),0,0));}
 let root=svg.split('>').next().ok_or("Invalid SVG")?;
 let w=attr(root,"width").and_then(|v|v.parse::<f64>().ok()).ok_or("Invalid width")?;let h=attr(root,"height").and_then(|v|v.parse::<f64>().ok()).ok_or("Invalid height")?;
 let vb:Vec<f64>=attr(root,"viewBox").map(|v|v.split_whitespace().filter_map(|t|t.parse().ok()).collect()).unwrap_or(vec![0.,0.,w,h]);
 if vb.len()!=4||w<=0.||h<=0.{return Err("Invalid viewBox");}let scale=(vb[2]/w+vb[3]/h)*0.5;let radius=scale*strength as f64*0.04;
 let(mut nodes,mut nm,mut edges,mut em,mut paths,mut prefixes,mut loops)=(Vec::new(),HashMap::new(),Vec::new(),HashMap::new(),Vec::new(),Vec::new(),Vec::new());let mut tail=svg;
 while let Some(i)=tail.find("<path "){
  prefixes.push(tail[..i].to_string());tail=&tail[i..];let end=tail.find('>').ok_or("Invalid path")?;let tag=tail[..=end].to_string();let d=attr(&tag,"d").ok_or("Missing path data")?.to_string();
  if d.chars().any(|c|c.is_ascii_alphabetic()&&!matches!(c,'M'|'L'|'C'|'Z'|'e'|'E')){return Err("Unsupported SVG command");}
  let text=d.replace('M'," M ").replace('L'," L ").replace('C'," C ").replace('Z'," Z ");let t:Vec<_>=text.split_whitespace().collect();let(mut j,mut op,mut cur,mut start,mut contour)=(0,"",0,0,Vec::new());let mut cmd=Vec::new();
  while j<t.len(){if matches!(t[j],"M"|"L"|"C"|"Z"){op=t[j];j+=1;}if op=="Z"{if cur!=start{let(id,rev)=add(cur,start,None,&nodes,&mut edges,&mut em);cmd.push(Cmd::E(id,rev));}cmd.push(Cmd::Z);if !contour.is_empty(){loops.push(std::mem::take(&mut contour));}cur=start;op="";continue;}
   let n=if op=="C"{6}else{2};if j+n>t.len(){return Err("Invalid coordinates");}let mut v=Vec::new();for s in &t[j..j+n]{let x=s.parse::<f64>().map_err(|_|"Invalid coordinate")?;if !x.is_finite(){return Err("Invalid coordinate");}v.push(x);}j+=n;
   let next=node([v[n-2],v[n-1]],&mut nodes,&mut nm);if op=="M"{if !contour.is_empty(){return Err("Open contours are not supported");}cur=next;start=next;contour.push(next);cmd.push(Cmd::M(next));op="L";continue;}
   if op!="L"&&op!="C"{return Err("Unsupported SVG command");}if cur!=next||op=="C"{let c=if op=="C"{Some([[v[0],v[1]],[v[2],v[3]]])}else{None};let(id,rev)=add(cur,next,c,&nodes,&mut edges,&mut em);cmd.push(Cmd::E(id,rev));}cur=next;contour.push(next);
  }
  if !contour.is_empty(){return Err("Open contours are not supported");}paths.push(Path{tag,d,cmd});tail=&tail[end+1..];
 }
 if edges.iter().any(|e|e.uses.len()>2||(e.uses.len()==2&&e.uses[0]==e.uses[1])){return Err("Input has inconsistent shared edges");}
 let mut neighbors=vec![Vec::new();nodes.len()];for (i,e) in edges.iter().enumerate(){neighbors[e.a].push(i);neighbors[e.b].push(i);}
 let mut pinned=vec![false;nodes.len()];
 for ids in &loops{let lo=[ids.iter().map(|&i|nodes[i][0]).fold(f64::INFINITY,f64::min),ids.iter().map(|&i|nodes[i][1]).fold(f64::INFINITY,f64::min)];let hi=[ids.iter().map(|&i|nodes[i][0]).fold(f64::NEG_INFINITY,f64::max),ids.iter().map(|&i|nodes[i][1]).fold(f64::NEG_INFINITY,f64::max)];if ids.len()<4||(hi[0]-lo[0]).max(hi[1]-lo[1])<=4.*scale||area(ids,&nodes).abs()<1e-8{for &i in ids{pinned[i]=true;}}}
 let other=|e:&Edge,i:usize|if e.a==i{e.b}else{e.a};
 for i in 0..nodes.len(){let p=nodes[i];if neighbors[i].len()!=2||p[0]<=vb[0]+1e-6||p[0]>=vb[0]+vb[2]-1e-6||p[1]<=vb[1]+1e-6||p[1]>=vb[1]+vb[3]-1e-6{pinned[i]=true;continue;}let a=nodes[other(&edges[neighbors[i][0]],i)];let b=nodes[other(&edges[neighbors[i][1]],i)];let u=[a[0]-p[0],a[1]-p[1]];let v=[b[0]-p[0],b[1]-p[1]];let dot=u[0]*v[0]+u[1]*v[1];let den=u[0].hypot(u[1])*v[0].hypot(v[1]);if den<1e-12||(sharp&&(dot>0.342*den||(dot>=-1e-9&&u[0].hypot(u[1])>4.*radius&&v[0].hypot(v[1])>4.*radius))){pinned[i]=true;}}
 let mut pos=nodes.clone();for _ in 0..1+(strength as usize+9)/10{for weight in [0.45,-0.47]{let mut next=pos.clone();for i in 0..nodes.len(){if pinned[i]{continue;}let a=other(&edges[neighbors[i][0]],i);let b=other(&edges[neighbors[i][1]],i);next[i]=clamp(std::array::from_fn(|j|pos[i][j]+weight*((pos[a][j]+pos[b][j])*0.5-pos[i][j])),nodes[i],radius);}pos=next;}}
 for ids in &loops{let a=area(ids,&nodes);let b=area(ids,&pos);if a.abs()>1e-8&&(a*b<=0.||b.abs()<a.abs()*0.25){return Err("Smoothing would erase a detail");}}
 let mut controls=Vec::new();for e in &edges{
  let p=pos[e.a];let q=pos[e.b];let old=e.c.unwrap_or([std::array::from_fn(|j|nodes[e.a][j]+(nodes[e.b][j]-nodes[e.a][j])/3.),std::array::from_fn(|j|nodes[e.a][j]+2.*(nodes[e.b][j]-nodes[e.a][j])/3.)]);let mut cs=old;
  for (side,i) in [e.a,e.b].into_iter().enumerate(){let base=std::array::from_fn::<_,2,_>(|j|old[side][j]+pos[i][j]-nodes[i][j]);cs[side]=base;if !pinned[i]&&neighbors[i].len()==2{let a=other(&edges[neighbors[i][0]],i);let b=other(&edges[neighbors[i][1]],i);let mut tangent=[pos[b][0]-pos[a][0],pos[b][1]-pos[a][1]];let to=if side==0{q}else{p};if tangent[0]*(to[0]-pos[i][0])+tangent[1]*(to[1]-pos[i][1])<0.{tangent=tangent.map(|v|-v);}let n=tangent[0].hypot(tangent[1]);if n>1e-12{let length=(base[0]-pos[i][0]).hypot(base[1]-pos[i][1]);let t=strength as f64/100.;cs[side]=std::array::from_fn(|j|base[j]*(1.-t)+(pos[i][j]+tangent[j]*length/n)*t);}}cs[side]=clamp(cs[side],old[side],radius);}
  let d=[q[0]-p[0],q[1]-p[1]];let bent=cs.iter().any(|c|((c[0]-p[0])*d[1]-(c[1]-p[1])*d[0]).abs()>1e-6);controls.push(if e.c.is_some()||bent{Some(cs)}else{None});
 }
 if pos==nodes&&edges.iter().zip(&controls).all(|(e,c)|e.c==*c){return Ok((svg.to_string(),nodes.len(),0));}
 let moved=pos.iter().zip(&nodes).filter(|(p,q)|(p[0]-q[0]).abs()+(p[1]-q[1]).abs()>1e-6).count();let mut output=String::new();
 for (path,prefix) in paths.iter().zip(prefixes){output.push_str(&prefix);let mut d=String::new();for c in &path.cmd{match c{Cmd::M(i)=>{write!(d,"M{:0.6} {:0.6} ",pos[*i][0],pos[*i][1]).unwrap();},Cmd::Z=>d.push_str("Z "),Cmd::E(id,rev)=>{let e=&edges[*id];let end=pos[if *rev{e.a}else{e.b}];if let Some(c)=controls[*id]{let(a,b)=if *rev{(c[1],c[0])}else{(c[0],c[1])};write!(d,"C{:0.6} {:0.6} {:0.6} {:0.6} {:0.6} {:0.6} ",a[0],a[1],b[0],b[1],end[0],end[1]).unwrap();}else{write!(d,"L{:0.6} {:0.6} ",end[0],end[1]).unwrap();}}}}
  output.push_str(&path.tag.replacen(&format!("d=\"{}\"",path.d),&format!("d=\"{d}\""),1));
 }output.push_str(tail);if !output.contains("data-post-smoothed="){output=output.replacen("<svg ","<svg data-post-smoothed=\"true\" ",1);}Ok((output,nodes.len(),moved))
}
