// SPDX-License-Identifier: MIT
// Four-connected regional means and adjacent Ward-SSE merge, desktop/photo_regions.py + region_merge.py.
use std::collections::{BTreeSet,BinaryHeap};
use std::cmp::Ordering;
#[derive(Clone)]struct Edge{cost:f64,a:usize,b:usize,va:u32,vb:u32}
impl PartialEq for Edge{fn eq(&self,o:&Self)->bool{self.cmp(o)==Ordering::Equal}}impl Eq for Edge{}
impl PartialOrd for Edge{fn partial_cmp(&self,o:&Self)->Option<Ordering>{Some(self.cmp(o))}}
impl Ord for Edge{fn cmp(&self,o:&Self)->Ordering{o.cost.total_cmp(&self.cost).then(o.a.cmp(&self.a)).then(o.b.cmp(&self.b)).then(o.va.cmp(&self.va)).then(o.vb.cmp(&self.vb))}}
fn cost(a:usize,b:usize,areas:&[f64],sums:&[[f64;3]])->f64{(0..3).map(|c|(sums[a][c]/areas[a]-sums[b][c]/areas[b]).powi(2)).sum::<f64>()*areas[a]*areas[b]/(areas[a]+areas[b])}
fn push(heap:&mut BinaryHeap<Edge>,a:usize,b:usize,areas:&[f64],sums:&[[f64;3]],versions:&[u32]){let(a,b)=if a<b{(a,b)}else{(b,a)};heap.push(Edge{cost:cost(a,b,areas,sums),a,b,va:versions[a],vb:versions[b]});}
pub fn components(labels:&[u8],a:&[u8],w:usize,h:usize,k:usize)->(Vec<i32>,Vec<[u8;3]>){
 let mut regions=vec![-1i32;w*h];let mut palette=Vec::new();let mut queue=Vec::new();
 for c in 0..k{for start in 0..w*h{if labels[start]!=c as u8||regions[start]>=0{continue;}let id=palette.len() as i32;queue.clear();queue.push(start);regions[start]=id;let mut p=0;let mut sums=[0u64;3];while p<queue.len(){let i=queue[p];p+=1;for j in 0..3{sums[j]+=a[4*i+j] as u64;}let x=i%w;let y=i/w;for neighbor in [if x>0{Some(i-1)}else{None},if x+1<w{Some(i+1)}else{None},if y>0{Some(i-w)}else{None},if y+1<h{Some(i+w)}else{None}].into_iter().flatten(){if regions[neighbor]<0&&labels[neighbor]==c as u8{regions[neighbor]=id;queue.push(neighbor);}}}palette.push(sums.map(|s|(s as f64/queue.len() as f64).round_ties_even() as u8));}}
 (regions,palette)
}
pub fn target(labels:&[u8],a:&[u8],w:usize,h:usize,detail:usize)->usize{
 let mut edges=0u64;for y in 0..h{for x in 0..w{let i=y*w+x;if x>0&&labels[i]!=labels[i-1]{edges+=1;}if y>0&&labels[i]!=labels[i-w]{edges+=1;}}}
 let mut hist=[0u64;12];for p in a.chunks_exact(4){if p[3]<128{continue;}let r=p[0] as i32;let g=p[1] as i32;let b=p[2] as i32;let v=r.max(g).max(b);let d=v-r.min(g).min(b);if v<32||d==0{continue;}let sdiv=((255*4096) as f64/v as f64).round_ties_even() as i32;let sat=(d*sdiv+2048)>>12;if sat<32{continue;}let hd=((180*4096) as f64/(6*d) as f64).round_ties_even() as i32;let base=if v==r{g-b}else if v==g{b-r+2*d}else{r-g+4*d};let hue=((base*hd+2048)>>12).rem_euclid(180);hist[(hue*12/180) as usize]+=1;}
 let total=hist.iter().sum::<u64>().max(1) as f64;let entropy=hist.iter().filter(|&&n|n>0).map(|&n|{let p=n as f64/total;-p*p.log2()}).sum::<f64>();let diversity=(entropy/3.2).clamp(0.6,1.05);
 (diversity*(edges as f64).powi(2)/(w*h) as f64/[40.,16.,6.][detail]).round_ties_even().max(128.) as usize
}
pub fn merge(labels:&mut [i32],palette:&mut Vec<[u8;3]>,w:usize,h:usize,target:usize){
 let n=palette.len();if n<=target{return;}let mut areas=vec![0.;n];for &c in labels.iter().filter(|&&c|c>=0){areas[c as usize]+=1.;}let mut sums:Vec<[f64;3]>=palette.iter().enumerate().map(|(i,p)|p.map(|c|c as f64*areas[i])).collect();let mut neighbors=vec![BTreeSet::new();n];
 for y in 0..h{for x in 0..w{let i=y*w+x;let a=labels[i];if a<0{continue;}for b in [if x+1<w{labels[i+1]}else{-1},if y+1<h{labels[i+w]}else{-1}]{if b<0||a==b{continue;}neighbors[a as usize].insert(b as usize);neighbors[b as usize].insert(a as usize);}}}
 let mut parent:Vec<usize>=(0..n).collect();let mut versions=vec![0u32;n];let mut heap=BinaryHeap::new();for a in 0..n{for &b in &neighbors[a]{if a<b{push(&mut heap,a,b,&areas,&sums,&versions);}}}let mut remaining=n;
 while remaining>target{let Some(e)=heap.pop()else{break;};let(a,b)=(e.a,e.b);if parent[a]!=a||parent[b]!=b||versions[a]!=e.va||versions[b]!=e.vb{continue;}parent[b]=a;areas[a]+=areas[b];for c in 0..3{sums[a][c]+=sums[b][c];}versions[a]+=1;remaining-=1;let adjacent:BTreeSet<_>=neighbors[a].union(&neighbors[b]).copied().filter(|&v|v!=a&&v!=b).collect();neighbors[a]=adjacent.clone();neighbors[b].clear();for c in adjacent{neighbors[c].remove(&b);neighbors[c].insert(a);push(&mut heap,a,c,&areas,&sums,&versions);}}
 for i in 0..n{let mut r=i;while parent[r]!=r{r=parent[r];}parent[i]=r;}let roots:BTreeSet<_>=parent.iter().copied().collect();let mut remap=vec![0;n];let mut out=Vec::new();for r in roots{remap[r]=out.len();out.push(std::array::from_fn(|c|(sums[r][c]/areas[r]).round_ties_even() as u8));}for v in labels{if *v>=0{*v=remap[parent[*v as usize]] as i32;}}*palette=out;
}
