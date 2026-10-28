// Standalone smoothing of finished SVG geometry. No raster or palette changes.
use std::collections::HashMap;
use std::fmt::Write;
type P=[f64;2];
#[derive(Clone)]struct Edge{a:usize,b:usize,c:Option<[P;2]>,uses:Vec<bool>}
#[derive(Clone,Copy)]enum Cmd{M,E(usize,bool),Z}
struct Path{tag:String,d:String,cmd:Vec<Cmd>}
fn attr<'a>(s:&'a str,k:&str)->Option<&'a str>{let n=format!("{k}=\"");let i=s.match_indices(&n).find(|(i,_)|*i>0&&s.as_bytes()[i-1].is_ascii_whitespace())?.0+n.len();let r=&s[i..];Some(&r[..r.find('"')?])}
fn node(p:P,nodes:&mut Vec<P>,map:&mut HashMap<[i64;2],usize>)->usize{let q=p.map(|v|(v*1e6).round() as i64);*map.entry(q).or_insert_with(||{nodes.push(q.map(|v|v as f64/1e6));nodes.len()-1})}
fn add(a:usize,b:usize,c:Option<[P;2]>,nodes:&[P],edges:&mut Vec<Edge>,map:&mut HashMap<Vec<i64>,usize>)->(usize,bool){
 let mut f=vec![if c.is_some(){1}else{0}];f.extend(nodes[a].map(|v|(v*1e6).round() as i64));if let Some(cs)=c{for p in cs{f.extend(p.map(|v|(v*1e6).round() as i64));}}f.extend(nodes[b].map(|v|(v*1e6).round() as i64));
 let mut r=vec![f[0]];for pair in f[1..].chunks_exact(2).rev(){r.extend(pair);}let rev=f>r;let key=if rev{r}else{f};
 let id=*map.entry(key).or_insert_with(||{edges.push(if rev{Edge{a:b,b:a,c:c.map(|v|[v[1],v[0]]),uses:Vec::new()}}else{Edge{a,b,c,uses:Vec::new()}});edges.len()-1});edges[id].uses.push(rev);(id,rev)
}
#[derive(Clone)]struct Curve{a:usize,b:usize,c:Option<[P;2]>,members:Vec<(usize,bool)>,samples:Vec<P>,active:bool}
fn dist(a:P,b:P)->f64{(a[0]-b[0]).hypot(a[1]-b[1])}
fn lerp(a:P,b:P,t:f64)->P{[a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t]}
fn sample(a:P,b:P,c:Option<[P;2]>)->Vec<P>{if let Some(c)=c{(0..=32).map(|i|{let t=i as f64/32.;let u=1.-t;std::array::from_fn(|j|u*u*u*a[j]+3.*u*u*t*c[0][j]+3.*u*t*t*c[1][j]+t*t*t*b[j])}).collect()}else{vec![a,b]}}
fn signed_area(points:&[P])->f64{points.windows(2).map(|p|p[0][0]*p[1][1]-p[1][0]*p[0][1]).sum::<f64>()*0.5}
fn distance(p:P,line:&[P])->f64{line.windows(2).map(|s|{let d=[s[1][0]-s[0][0],s[1][1]-s[0][1]];let den=d[0]*d[0]+d[1]*d[1];let t=if den>0.{((p[0]-s[0][0])*d[0]+(p[1]-s[0][1])*d[1])/den}else{0.};dist(p,lerp(s[0],s[1],t.clamp(0.,1.)))}).fold(f64::INFINITY,f64::min)}
fn oriented(g:&Curve,reverse:bool)->(Vec<P>,Vec<(usize,bool)>){let mut p=g.samples.clone();let mut m=g.members.clone();if reverse{p.reverse();m.reverse();for x in &mut m{x.1=!x.1;}}(p,m)}
fn tangent(g:&Curve,node:usize,nodes:&[P])->P{let c=if node==g.a{g.c.map(|c|c[0]).unwrap_or(nodes[g.b])}else{g.c.map(|c|c[1]).unwrap_or(nodes[g.a])};let d=[c[0]-nodes[node][0],c[1]-nodes[node][1]];let len=d[0].hypot(d[1]);if len>1e-10{d.map(|x|x/len)}else{[0.,0.]}}
fn fit(points:&[P],u:P,v:P,tol:f64)->Option<Option<[P;2]>>{
 let a=points[0];let b=*points.last()?;let mut lengths=vec![0.];for w in points.windows(2){lengths.push(lengths.last().unwrap()+dist(w[0],w[1]));}let total=*lengths.last()?;if total<1e-8{return None;}
 // Original polyline samples are retained across merges: error cannot accumulate.
 let chord=dist(a,b);if chord>0.&&points.iter().all(|&p|distance(p,&[a,b])<=tol*0.75){return Some(None);}
 let(mut aa,mut ab,mut bb,mut ax,mut bx)=(0.,0.,0.,0.,0.);
 for (p,l) in points.iter().zip(lengths){let t=l/total;let s=1.-t;let f=3.*s*s*t;let g=3.*s*t*t;let base=std::array::from_fn::<_,2,_>(|j|a[j]*(s*s*s+f)+b[j]*(t*t*t+g));let x=u.map(|x|x*f);let y=v.map(|x|x*g);for j in 0..2{aa+=x[j]*x[j];ab+=x[j]*y[j];bb+=y[j]*y[j];ax+=x[j]*(p[j]-base[j]);bx+=y[j]*(p[j]-base[j]);}}
 let det=aa*bb-ab*ab;if det.abs()<1e-12{return None;}let al=(ax*bb-bx*ab)/det;let be=(bx*aa-ax*ab)/det;if al<0.||be<0.||al>total||be>total{return None;}
 let controls=[std::array::from_fn(|j|a[j]+u[j]*al),std::array::from_fn(|j|b[j]+v[j]*be)];let candidate=sample(a,b,Some(controls));
 if points.iter().any(|&p|distance(p,&candidate)>tol*0.75)||candidate.iter().any(|&p|distance(p,points)>tol*0.75){None}else{Some(Some(controls))}
}
pub fn clean(svg:&str,min_area:f64,tolerance:f64,protect:bool)->Result<(String,usize,usize,usize,usize),&'static str>{
 if svg.len()>32_000_000{return Err("SVG is too large");}if svg.contains("transform="){return Err("Transformed paths are not supported");}
 
 let root=svg.split('>').next().ok_or("Invalid SVG")?;
 let w=attr(root,"width").and_then(|v|v.parse::<f64>().ok()).ok_or("Invalid width")?;let h=attr(root,"height").and_then(|v|v.parse::<f64>().ok()).ok_or("Invalid height")?;
 let vb:Vec<f64>=attr(root,"viewBox").map(|v|v.split_whitespace().filter_map(|t|t.parse().ok()).collect()).unwrap_or(vec![0.,0.,w,h]);
 if vb.len()!=4||w<=0.||h<=0.{return Err("Invalid viewBox");}let scale=(vb[2]/w+vb[3]/h)*0.5;
 let(mut nodes,mut nm,mut edges,mut em,mut paths,mut prefixes,mut loops)=(Vec::new(),HashMap::new(),Vec::new(),HashMap::new(),Vec::new(),Vec::new(),Vec::new());let mut tail=svg;
 while let Some(i)=tail.find("<path "){
  prefixes.push(tail[..i].to_string());tail=&tail[i..];let end=tail.find('>').ok_or("Invalid path")?;let tag=tail[..=end].to_string();let d=attr(&tag,"d").ok_or("Missing path data")?.to_string();
  if d.chars().any(|c|c.is_ascii_alphabetic()&&!matches!(c,'M'|'L'|'C'|'Z'|'e'|'E')){return Err("Unsupported SVG command");}
  let text=d.replace('M'," M ").replace('L'," L ").replace('C'," C ").replace('Z'," Z ");let t:Vec<_>=text.split_whitespace().collect();let(mut j,mut op,mut cur,mut start,mut contour)=(0,"",0,0,Vec::new());let mut cmd=Vec::new();
  while j<t.len(){if matches!(t[j],"M"|"L"|"C"|"Z"){op=t[j];j+=1;}if op=="Z"{if cur!=start{let(id,rev)=add(cur,start,None,&nodes,&mut edges,&mut em);cmd.push(Cmd::E(id,rev));}cmd.push(Cmd::Z);if !contour.is_empty(){loops.push(std::mem::take(&mut contour));}cur=start;op="";continue;}
   let n=if op=="C"{6}else{2};if j+n>t.len(){return Err("Invalid coordinates");}let mut v=Vec::new();for s in &t[j..j+n]{let x=s.parse::<f64>().map_err(|_|"Invalid coordinate")?;if !x.is_finite(){return Err("Invalid coordinate");}v.push(x);}j+=n;
   let next=node([v[n-2],v[n-1]],&mut nodes,&mut nm);if op=="M"{if !contour.is_empty(){return Err("Open contours are not supported");}cur=next;start=next;contour.push(next);cmd.push(Cmd::M);op="L";continue;}
   if op!="L"&&op!="C"{return Err("Unsupported SVG command");}if cur!=next||op=="C"{let c=if op=="C"{Some([[v[0],v[1]],[v[2],v[3]]])}else{None};let(id,rev)=add(cur,next,c,&nodes,&mut edges,&mut em);cmd.push(Cmd::E(id,rev));}cur=next;contour.push(next);
  }
  if !contour.is_empty(){return Err("Open contours are not supported");}paths.push(Path{tag,d,cmd});tail=&tail[end+1..];
 }
 if edges.iter().any(|e|e.uses.len()>2||(e.uses.len()==2&&e.uses[0]==e.uses[1])){return Err("Input has inconsistent shared edges");}
 let mut neighbors=vec![Vec::new();nodes.len()];for(i,e)in edges.iter().enumerate(){neighbors[e.a].push(i);neighbors[e.b].push(i);}
 let mut cycles:Vec<Vec<(usize,bool)>>=Vec::new();let mut path_cycles=Vec::new();for path in &paths{let mut ids=Vec::new();let mut current=Vec::new();for cmd in &path.cmd{match *cmd{Cmd::M=>{},Cmd::E(e,r)=>current.push((e,r)),Cmd::Z=>{ids.push(cycles.len());cycles.push(std::mem::take(&mut current));}}}path_cycles.push(ids);}
 let before=cycles.iter().map(Vec::len).sum();let mut grouped:HashMap<Vec<usize>,Vec<usize>>=HashMap::new();for(i,cycle)in cycles.iter().enumerate(){let mut key:Vec<_>=cycle.iter().map(|e|e.0).collect();key.sort_unstable();grouped.entry(key).or_default().push(i);}
 let mut remove=vec![false;cycles.len()];let(mut removed,mut protected)=(0,0);
 // Only whole isolated interfaces can disappear. Interfaces meeting a junction stay intact.
 let mut keys:Vec<_>=grouped.into_iter().collect();keys.sort_by(|a,b|a.0.cmp(&b.0));
 for(key,owners)in keys{if min_area<=0.||key.is_empty(){continue;}let mut points=Vec::new();for &(id,rev)in &cycles[owners[0]]{let e=&edges[id];let mut ps=sample(nodes[e.a],nodes[e.b],e.c);if rev{ps.reverse();}points.extend(ps.into_iter().skip(if points.is_empty(){0}else{1}));}if points.len()<3{continue;}
  let area=signed_area(&points).abs()/scale.powi(2);if area>min_area||area<1e-10{continue;}
  let lo:Vec<f64>=(0..2).map(|j|points.iter().map(|p|p[j]).fold(f64::INFINITY,f64::min)).collect();let hi:Vec<f64>=(0..2).map(|j|points.iter().map(|p|p[j]).fold(f64::NEG_INFINITY,f64::max)).collect();let dx=hi[0]-lo[0];let dy=hi[1]-lo[1];
  let isolated=key.iter().all(|&id|[edges[id].a,edges[id].b].iter().all(|&i|neighbors[i].len()==2));let frame=lo[0]<=vb[0]+1e-6||lo[1]<=vb[1]+1e-6||hi[0]>=vb[0]+vb[2]-1e-6||hi[1]>=vb[1]+vb[3]-1e-6;
  if !isolated||frame||(protect&&dx.max(dy)>8.*dx.min(dy).max(1e-8)){protected+=1;continue;}
  // A shared boundary must be removed in every owning contour, never on one side alone.
  if key.iter().any(|&id|edges[id].uses.len()!=owners.len()){protected+=1;continue;}for i in owners{remove[i]=true;}removed+=1;
 }
 let mut deleted=vec![false;edges.len()];for(i,cycle)in cycles.iter().enumerate(){if remove[i]{for &(id,_)in cycle{deleted[id]=true;}}}
 let mut curves:Vec<_>=edges.iter().enumerate().map(|(i,e)|Curve{a:e.a,b:e.b,c:e.c,members:vec![(i,false)],samples:sample(nodes[e.a],nodes[e.b],e.c),active:!deleted[i]}).collect();let mut assigned:Vec<_>=(0..edges.len()).map(|i|(i,false)).collect();for list in &mut neighbors{list.retain(|&e|!deleted[e]);}
 let tol=tolerance.clamp(0.,2.)*scale;
 if tol>0.{for _ in 0..8{let mut merges=0;for node in 0..nodes.len(){let ids=&neighbors[node];if ids.len()!=2{continue;}let (i,j)=(ids[0],ids[1]);let(a,b)=(&curves[i],&curves[j]);if !a.active||!b.active||a.members.len()+b.members.len()>64{continue;}
  let x=if a.a==node{a.b}else{a.a};let y=if b.a==node{b.b}else{b.a};if x==y||neighbors[x].iter().any(|&k|k!=i&&(curves[k].a==y||curves[k].b==y)){continue;}
  let p=nodes[node];if p[0]<=vb[0]+1e-6||p[1]<=vb[1]+1e-6||p[0]>=vb[0]+vb[2]-1e-6||p[1]>=vb[1]+vb[3]-1e-6{continue;}
  let ta=tangent(a,node,&nodes);let tb=tangent(b,node,&nodes);if protect&&ta[0]*tb[0]+ta[1]*tb[1]>-0.906307787{continue;}
  let(mut samples,mut members)=oriented(a,a.a==node);let(ps,ms)=oriented(b,b.b==node);samples.extend(ps.into_iter().skip(1));members.extend(ms);let u=tangent(a,x,&nodes);let v=tangent(b,y,&nodes);let Some(c)=fit(&samples,u,v,tol)else{continue;};
  let id=curves.len();for &(old,r)in &members{assigned[old]=(id,r);}curves[i].active=false;curves[j].active=false;curves.push(Curve{a:x,b:y,c,members,samples,active:true});neighbors[node].clear();neighbors[x].retain(|&e|e!=i);neighbors[y].retain(|&e|e!=j);neighbors[x].push(id);neighbors[y].push(id);merges+=1;
 }if merges==0{break;}}}
 let mut after=0;let mut output=String::new();for((path,prefix),ids)in paths.iter().zip(prefixes).zip(path_cycles){output.push_str(&prefix);let mut d=String::new();for ci in ids{if remove[ci]{continue;}let mut list=Vec::new();for &(e,r)in &cycles[ci]{let(id,flip)=assigned[e];let item=(id,r^flip);if list.last()!=Some(&item){list.push(item);}}if list.len()>1&&list.first()==list.last(){list.pop();}if list.is_empty(){continue;}after+=list.len();let(g,r)=list[0];let start=nodes[if r{curves[g].b}else{curves[g].a}];write!(d,"M{:.6} {:.6} ",start[0],start[1]).unwrap();for(id,r)in list{let g=&curves[id];let end=nodes[if r{g.a}else{g.b}];if let Some(c)=g.c{let(a,b)=if r{(c[1],c[0])}else{(c[0],c[1])};write!(d,"C{:.6} {:.6} {:.6} {:.6} {:.6} {:.6} ",a[0],a[1],b[0],b[1],end[0],end[1]).unwrap();}else{write!(d,"L{:.6} {:.6} ",end[0],end[1]).unwrap();}}d.push_str("Z ");}
 if !d.is_empty(){output.push_str(&path.tag.replacen(&format!("d=\"{}\"",path.d),&format!("d=\"{d}\""),1));}}
 output.push_str(tail);if before==after&&removed==0{return Ok((svg.to_string(),before,after,removed,protected));}if !output.contains("data-post-cleaned="){output=output.replacen("<svg ","<svg data-post-cleaned=\"true\" ",1);}Ok((output,before,after,removed,protected))
}