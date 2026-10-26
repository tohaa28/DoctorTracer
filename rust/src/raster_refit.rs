// SPDX-License-Identifier: MIT
// Independent adaptive 4x/2x nonzero-winding scanline renderer for our M/L/C/Z export dialect.
// Search one shared cubic tension against the complete premultiplied input raster.
use std::fmt::Write;
fn tokens(d:&str)->Vec<String>{let a=d.as_bytes();let mut i=0;let mut out=Vec::new();while i<a.len(){if a[i].is_ascii_alphabetic(){out.push((a[i] as char).to_string());i+=1;}else if a[i].is_ascii_digit()||a[i]==b'-'||a[i]==b'+'||a[i]==b'.'{let start=i;i+=1;while i<a.len(){if a[i].is_ascii_digit()||a[i]==b'.'{i+=1;}else if a[i]==b'e'||a[i]==b'E'{i+=1;if i<a.len()&&(a[i]==b'-'||a[i]==b'+'){i+=1;}}else{break;}}out.push(d[start..i].to_string());}else{i+=1;}}out}
fn attr<'a>(tag:&'a str,key:&str)->Option<&'a str>{let needle=format!(" {key}=\"");let start=if tag.starts_with(&needle[1..]){needle.len()-1}else{tag.find(&needle)?+needle.len()};let rest=&tag[start..];Some(&rest[..rest.find('"')?])}
// Path visitors are explicit below: reject other elements/transforms at the ABI.
fn adjust(svg:&str,tension:f64)->Option<String>{
 if tension==1.{return Some(svg.to_string());}let mut out=String::new();let mut tail=svg;
 while let Some(i)=tail.find("<path "){out.push_str(&tail[..i]);tail=&tail[i..];let end=tail.find('>')?;let tag=&tail[..end];let d=attr(tag,"d")?;let ts=tokens(d);let mut i=0;let mut current=[0.;2];let mut start=[0.;2];let mut data=String::new();
  while i<ts.len(){let cmd=ts[i].as_str();i+=1;let count=match cmd{"M"|"L"=>2,"C"=>6,"Z"|"z"=>0,_=>return None};if i+count>ts.len(){return None;}let mut p=Vec::new();for token in &ts[i..i+count]{p.push(token.parse::<f64>().ok()?);}i+=count;
   if cmd=="C"{for j in 0..2{let q1=current[j]+(p[4+j]-current[j])/3.;let q2=current[j]+2.*(p[4+j]-current[j])/3.;p[j]=q1+(p[j]-q1)*tension;p[2+j]=q2+(p[2+j]-q2)*tension;}}
   if count>0{current=[p[count-2],p[count-1]];if cmd=="M"{start=current;}}else{current=start;}
   data.push_str(cmd);for v in p{write!(data,"{v:.6} ").ok()?;}
  }
  let needle=format!(" d=\"{d}\"");let changed=tag.replacen(&needle,&format!(" d=\"{data}\""),1);out.push_str(&changed);out.push('>');tail=&tail[end+1..];
 }out.push_str(tail);Some(out)
}
fn energy(svg:&str,a:&[u8],w:usize,h:usize)->Option<u64>{
 let samples=if w*h<=1_000_000{4}else{2};let scale=samples as f64;let sw=w*samples;let sh=h*samples;let mut canvas=vec![[255u8,255,255,0];sw*sh];
 for text in svg.split("<path ").skip(1){let tag=&text[..text.find('>')?];let fill=attr(tag,"fill")?;if fill.len()!=7||!fill.starts_with('#'){return None;}let ink=[u8::from_str_radix(&fill[1..3],16).ok()?,u8::from_str_radix(&fill[3..5],16).ok()?,u8::from_str_radix(&fill[5..7],16).ok()?,255];let ts=tokens(attr(tag,"d")?);let mut rows=vec![Vec::<(f64,i32)>::new();sh];
  let mut edge=|p:[f64;2],q:[f64;2]|{if p[1]==q[1]{return;}let low=p[1].min(q[1]);let high=p[1].max(q[1]);let lo=((low*scale-0.5).ceil() as isize).max(0) as usize;let hi=((high*scale-0.5).ceil() as isize).max(0).min(sh as isize) as usize;for y in lo..hi{let yy=(y as f64+0.5)/scale;let x=p[0]+(yy-p[1])*(q[0]-p[0])/(q[1]-p[1]);rows[y].push((x*scale,if q[1]>p[1]{1}else{-1}));}};
  let(mut cur,mut start)=([0.;2],[0.;2]);let mut i=0;
  while i<ts.len(){let cmd=ts[i].as_str();i+=1;let n=match cmd{"M"|"L"=>2,"C"=>6,"Z"|"z"=>0,_=>return None};let p:Vec<f64>=ts.get(i..i+n)?.iter().map(|v|v.parse::<f64>()).collect::<Result<_,_>>().ok()?;i+=n;
   match cmd{"M"=>{cur=[p[0],p[1]];start=cur;},"L"=>{let q=[p[0],p[1]];edge(cur,q);cur=q;},"C"=>{let from=cur;let mut prev=cur;let extent=(0..2).map(|j|(p[j]-from[j]).abs()+(p[2+j]-p[j]).abs()+(p[4+j]-p[2+j]).abs()).fold(0f64,f64::max);let steps=(extent*2.).ceil().clamp(4.,128.) as usize;for k in 1..=steps{let t=k as f64/steps as f64;let u=1.-t;let q=std::array::from_fn::<_,2,_>(|j|u*u*u*from[j]+3.*u*u*t*p[j]+3.*u*t*t*p[2+j]+t*t*t*p[4+j]);edge(prev,q);prev=q;}cur=[p[4],p[5]];},_=>{edge(cur,start);cur=start;}}
  }
  for(y,row)in rows.iter_mut().enumerate(){row.sort_by(|a,b|a.0.total_cmp(&b.0));let mut winding=0;let mut begin=0f64;for &(x,direction)in row.iter(){if winding!=0{let lo=((begin-0.5).ceil() as isize).max(0) as usize;let hi=((x-0.5).ceil() as isize).max(0).min(sw as isize) as usize;if lo<hi{canvas[y*sw+lo..y*sw+hi].fill(ink);}}winding+=direction;begin=x;}}
 }
 let mut sum=0u64;for y in 0..h{for x in 0..w{let i=y*w+x;for j in 0..4{let mut actual=0i64;for dy in 0..samples{for dx in 0..samples{actual+=canvas[(samples*y+dy)*sw+samples*x+dx][j] as i64;}}let area=(samples*samples) as i64;let target=if j==3{a[4*i+3] as i64*area}else{((a[4*i+j] as i64*a[4*i+3] as i64+255*(255-a[4*i+3] as i64)+127)/255)*area};sum+=((actual-target).pow(2) as u64)*if j==3{3}else{1};}}}Some(sum)
}
pub fn refit(svg:&str,a:&[u8],w:usize,h:usize)->(String,u64,u64,f64){
 let Some(initial)=energy(svg,a,w,h)else{return(svg.to_string(),0,0,1.);};let mut best=initial;let mut result=svg.to_string();let mut tension=1.;for t in [0.75,1.25]{if let Some(candidate)=adjust(svg,t){if let Some(e)=energy(&candidate,a,w,h){if e<best{best=e;result=candidate;tension=t;}}}}(result,initial,best,tension)
}
#[cfg(test)]mod tests{#[test]fn identity(){let s="<svg><path fill=\"#ff0000\" d=\"M0 0 L8 0 L8 8 L0 8 Z\"/></svg>";let a=[255u8,0,0,255].repeat(64);let(_,before,after,_)=super::refit(s,&a,8,8);assert_eq!(before,0);assert_eq!(after,0);}}
