// SPDX-License-Identifier: MIT
// Same bounded local coverage loss as desktop/edge_fit.py. Shared vertex/radius.
use std::collections::BTreeMap;
fn observe(a:&[u8],w:usize,h:usize,p:[f64;2])->[f64;4]{
 let x=(p[0]-0.5).clamp(0.,w as f64-1.000001);let y=(p[1]-0.5).clamp(0.,h as f64-1.000001);let ix=x.floor() as usize;let iy=y.floor() as usize;let fx=x-ix as f64;let fy=y-iy as f64;let mut value=[0.;4];
 for(dx,dy,weight)in[(0,0,(1.-fx)*(1.-fy)),(1,0,fx*(1.-fy)),(0,1,(1.-fx)*fy),(1,1,fx*fy)]{let p=&a[4*((iy+dy)*w+ix+dx)..];let alpha=p[3] as f64/255.;for j in 0..3{value[j]+=p[j] as f64/255.*alpha*weight;}value[3]+=alpha*weight;}value
}
fn loss(a:&[u8],w:usize,h:usize,p:[f64;2],ink:[f64;4],delta:[f64;4],den:f64)->f64{let value=observe(a,w,h,p);let t=(0..4).map(|j|(value[j]-ink[j])*delta[j]).sum::<f64>()/den;(t-0.5).powi(2)}
fn neighbor(v:usize,d:usize,stride:usize)->usize{match d{0=>v+1,1=>v+stride,2=>v-1,_=>v-stride}}
pub fn fit(coords:&mut[[f64;2]],graph:&[u8],loops:&BTreeMap<i32,Vec<Vec<usize>>>,keep:&[bool],labels:&[i32],palette:&[[u8;3]],source:&[u8],w:usize,h:usize)->Vec<f64>{
 let stride=w+1;let mut pinned=vec![false;coords.len()];let mut previous=vec![usize::MAX;coords.len()];let mut following=previous.clone();
 for paths in loops.values(){for path in paths{if path.len()<=8{for &v in path{pinned[v]=true;}}let selected:Vec<_>=path.iter().copied().filter(|&v|keep[v]).collect();if selected.len()<3{continue;}for(i,&v)in selected.iter().enumerate(){if previous[v]==usize::MAX{previous[v]=selected[(i+selected.len()-1)%selected.len()];following[v]=selected[(i+1)%selected.len()];}}}}
 let original=coords.to_vec();let mut data=Vec::new();
 for v in 0..coords.len(){let x=v%stride;let y=v/stride;if pinned[v]||graph[v].count_ones()!=2||x<=1||x>=w-1||y<=1||y>=h-1{continue;}
  let mut colors=vec![labels[(y-1)*w+x-1],labels[(y-1)*w+x],labels[y*w+x-1],labels[y*w+x]];colors.sort_unstable();colors.dedup();if colors.len()!=2||colors[0]<0{continue;}
  let ink=std::array::from_fn::<_,4,_>(|j|if j==3{1.}else{palette[colors[0] as usize][j] as f64/255.});let delta=std::array::from_fn::<_,4,_>(|j|if j==3{0.}else{palette[colors[1] as usize][j] as f64/255.-ink[j]});let den=delta.iter().map(|v|v*v).sum::<f64>();if den<0.01{continue;}
  let mut ns:Vec<_>=(0..4).filter(|d|graph[v]&(1<<d)!=0).map(|d|neighbor(v,d,stride)).collect();ns.sort_unstable();let t=[original[ns[1]][0]-original[ns[0]][0],original[ns[1]][1]-original[ns[0]][1]];let len=(t[0]*t[0]+t[1]*t[1]).sqrt();if len<0.1{continue;}let normal=[-t[1]/len,t[0]/len];let base=original[v];let mut best=loss(source,w,h,base,ink,delta,den);
  for step in [-0.25,-0.125,0.125,0.25]{let p=[base[0]+step*normal[0],base[1]+step*normal[1]];let cost=loss(source,w,h,p,ink,delta,den)+0.02*step*step;if cost+1e-9<best{best=cost;coords[v]=p;}}
  data.push((v,ink,delta,den));
 }
 let mut radii=vec![1.5;coords.len()];
 for(v,ink,delta,den)in data{if previous[v]==usize::MAX{continue;}let corner=coords[v];let left=std::array::from_fn::<_,2,_>(|j|(coords[previous[v]][j]+corner[j])*0.5);let right=std::array::from_fn::<_,2,_>(|j|(coords[following[v]][j]+corner[j])*0.5);
  let cost=|radius:f64|{let near=|p:[f64;2]|{let d=[p[0]-corner[0],p[1]-corner[1]];let len=d[0].abs().max(d[1].abs()).max(1e-12);let f=(radius/len).min(1.);[corner[0]+d[0]*f,corner[1]+d[1]*f]};let enter=near(left);let leave=near(right);let mut e=0.;for t in [0.25f64,0.5,0.75]{let p=std::array::from_fn::<_,2,_>(|j|(1.-t).powi(2)*enter[j]+2.*t*(1.-t)*corner[j]+t*t*leave[j]);e+=loss(source,w,h,p,ink,delta,den);}e+0.002*(radius-1.5).powi(2)};
  let mut best=cost(1.5);for r in [0.5,1.,2.]{let value=cost(r);if value+1e-9<best{best=value;radii[v]=r;}}
 }radii
}
