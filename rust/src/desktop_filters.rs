// SPDX-License-Identifier: MIT
// Algorithm and integer rounding ported from desktop/gpu_filter.py and gpu_meanshift.py.
fn reflect(i:i32,n:usize)->usize{if n==1{return 0;}let period=2*n as i32-2;let j=i.rem_euclid(period);j.min(period-j) as usize}
pub fn bilateral(a:&[u8],w:usize,h:usize)->Vec<u8>{
 let weights:Vec<u32>=(0..5*766).map(|i|{let r=(i/766) as f64;let d=(i%766) as f64;(4096.*(-d*d/(2.*25f64.powi(2))-r/18.).exp()).round_ties_even() as u32}).collect();
 let mut out=a.to_vec();
 for y in 0..h{for x in 0..w{let i=4*(y*w+x);if a[i+3]<128{continue;}let mut sum=[0u32;3];let mut n=0;
  for dy in -2i32..=2{for dx in -2i32..=2{let r=dx*dx+dy*dy;if r>4{continue;}let j=4*(reflect(y as i32+dy,h)*w+reflect(x as i32+dx,w));if a[j+3]<128{continue;}
   let d=(0..3).map(|c|(a[i+c] as i32-a[j+c] as i32).unsigned_abs() as usize).sum::<usize>();let weight=weights[r as usize*766+d];n+=weight;for c in 0..3{sum[c]+=a[j+c] as u32*weight;}
  }}for c in 0..3{out[i+c]=((sum[c]+n/2)/n) as u8;}
 }}out
}
pub fn modes(a:&[u8],w:usize,h:usize,detail:usize)->Vec<u8>{
 let radius=[7,5,3][detail];let range2=[900,400,225][detail];let mut out=a.to_vec();
 for oy in 0..h{for ox in 0..w{let i=4*(oy*w+ox);if a[i+3]<128{continue;}let(mut x,mut y)=(ox,oy);let mut color=[a[i] as i32,a[i+1] as i32,a[i+2] as i32];
  for _ in 0..5{let(mut sx,mut sy,mut n)=(0usize,0usize,0usize);let mut sums=[0usize;3];
   for yy in y.saturating_sub(radius)..=(y+radius).min(h-1){for xx in x.saturating_sub(radius)..=(x+radius).min(w-1){let j=4*(yy*w+xx);if a[j+3]<128{continue;}let d=(0..3).map(|c|(a[j+c] as i32-color[c]).pow(2)).sum::<i32>();if d>range2{continue;}n+=1;sx+=xx;sy+=yy;for c in 0..3{sums[c]+=a[j+c] as usize;}}}
   if n==0{break;}let nx=(sx+n/2)/n;let ny=(sy+n/2)/n;let nc=std::array::from_fn(|c|((sums[c]+n/2)/n) as i32);let done=nx==x&&ny==y&&nc==color;x=nx;y=ny;color=nc;if done{break;}
  }for c in 0..3{out[i+c]=color[c] as u8;}
 }}out
}
pub fn segment(a:&[u8],w:usize,h:usize,palette:&[[u8;3]],strength:i32,aa:bool,radius:usize)->Vec<u8>{
 let mut labels=vec![255u8;w*h];let mut distance=vec![i32::MAX;w*h];
 for i in 0..w*h{if a[4*i+3]<128{continue;}for(k,p)in palette.iter().enumerate(){let d=(0..3).map(|c|(a[4*i+c] as i32-p[c] as i32).pow(2)).sum();if d<distance[i]{distance[i]=d;labels[i]=k as u8;}}}
 if aa{let old=labels.clone();for y in 0..h{for x in 0..w{let i=y*w+x;if old[i]==255{continue;}let mut allowed=[false;128];for yy in y.saturating_sub(radius)..=(y+radius).min(h-1){for xx in x.saturating_sub(radius)..=(x+radius).min(w-1){let j=yy*w+xx;if old[j]!=255&&distance[j]<576{allowed[old[j] as usize]=true;}}}let mut best=i32::MAX;for(k,p)in palette.iter().enumerate(){if !allowed[k]{continue;}let d=(0..3).map(|c|(a[4*i+c] as i32-p[c] as i32).pow(2)).sum();if d<best{best=d;labels[i]=k as u8;}}}}}
 if strength>0{for _ in 0..2{for phase in 0..2{let old=labels.clone();for y in 0..h{for x in 0..w{let i=y*w+x;if old[i]==255||(x+y)%2!=phase{continue;}let neighbors=[if x>0{old[i-1]}else{255},if x+1<w{old[i+1]}else{255},if y>0{old[i-w]}else{255},if y+1<h{old[i+w]}else{255}];let mut best=i32::MAX;for(k,p)in palette.iter().enumerate(){let energy=(0..3).map(|c|(a[4*i+c] as i32-p[c] as i32).pow(2)).sum::<i32>()+strength*neighbors.iter().filter(|&&v|v!=255&&v!=k as u8).count() as i32;if energy<best{best=energy;labels[i]=k as u8;}}}}}}}
 labels
}
fn median(a:&[u8],w:usize,h:usize)->Vec<u8>{let mut out=a.to_vec();for y in 0..h{for x in 0..w{let mut values=[0u8;9];let mut n=0;for dy in -1i32..=1{for dx in -1i32..=1{let xx=(x as i32+dx).clamp(0,w as i32-1) as usize;let yy=(y as i32+dy).clamp(0,h as i32-1) as usize;values[n]=a[yy*w+xx];n+=1;}}values.sort_unstable();out[y*w+x]=values[4];}}out}
pub fn clean(labels:&mut [u8],w:usize,h:usize,k:usize,min_area:usize,artifact:usize){
 if artifact>0{let med=median(labels,w,h);let different:Vec<bool>=labels.iter().zip(&med).map(|(a,b)|a!=b).collect();for y in 0..h{for x in 0..w{let i=y*w+x;if labels[i]==255||med[i]==255{continue;}let mut n=0;for dy in -1..=1{for dx in -1..=1{n+=different[reflect(y as i32+dy,h)*w+reflect(x as i32+dx,w)] as usize;}}if n>=if artifact==1{6}else{4}{labels[i]=med[i];}}}}
 if min_area==0{return;}let med=median(labels,w,h);let mut seen=vec![false;w*h];let mut queue=Vec::new();
 for color in 0..k{seen.fill(false);for start in 0..w*h{if seen[start]||labels[start]!=color as u8{continue;}queue.clear();queue.push(start);seen[start]=true;let mut p=0;while p<queue.len(){let i=queue[p];p+=1;let x=i%w;let y=i/w;for yy in y.saturating_sub(1)..=(y+1).min(h-1){for xx in x.saturating_sub(1)..=(x+1).min(w-1){let j=yy*w+xx;if !seen[j]&&labels[j]==color as u8{seen[j]=true;queue.push(j);}}}}if queue.len()<min_area{for &i in &queue{labels[i]=med[i];}}}}
}

pub fn resize2(a:&[u8],w:usize,h:usize)->Vec<u8>{
 let mut out=vec![0u8;w*h*16];for y in 0..h*2{for x in 0..w*2{
 let sx=(x as i32-1).div_euclid(2);let sy=(y as i32-1).div_euclid(2);let wx=if sx<0||sx>=w as i32-1{0}else if x%2==1{1}else{3};let wy=if y%2==1{1}else{3};let x0=sx.clamp(0,w as i32-1) as usize;let x1=(x0+1).min(w-1);let y0=sy.clamp(0,h as i32-1) as usize;let y1=(sy+1).clamp(0,h as i32-1) as usize;
 for c in 0..4{let h0=a[4*(y0*w+x0)+c] as u32*(4-wx)+a[4*(y0*w+x1)+c] as u32*wx;let h1=a[4*(y1*w+x0)+c] as u32*(4-wx)+a[4*(y1*w+x1)+c] as u32*wx;out[4*(y*w*2+x)+c]=(((h0*(4-wy)/4)+(h1*wy/4)+2)/4) as u8;}
 }}out
}

// Topology-aware small region cleanup: preserve contrast and elongated marks.
pub fn clean_aware(labels:&mut[u8],w:usize,h:usize,palette:&[[u8;3]],min_area:usize,artifact:usize){
 if artifact>0{clean(labels,w,h,palette.len(),0,artifact);}if min_area<=1{return;}
 let original=labels.to_vec();let mut seen=vec![false;labels.len()];
 for start in 0..labels.len(){if seen[start]||original[start]==255{continue;}let color=original[start];let mut queue=vec![start];seen[start]=true;let(mut x0,mut x1,mut y0,mut y1)=(start%w,start%w,start/w,start/w);let mut head=0;
  while head<queue.len(){let i=queue[head];head+=1;let x=i%w;let y=i/w;x0=x0.min(x);x1=x1.max(x);y0=y0.min(y);y1=y1.max(y);for yy in y.saturating_sub(1)..=(y+1).min(h-1){for xx in x.saturating_sub(1)..=(x+1).min(w-1){let j=yy*w+xx;if !seen[j]&&original[j]==color{seen[j]=true;queue.push(j);}}}}
  let bw=x1-x0+1;let bh=y1-y0+1;if queue.len()>=min_area||(bw.min(bh)<=2&&bw.max(bh)>=3){continue;}
  let mut neighbors=std::collections::BTreeSet::new();for &i in &queue{let x=i%w;let y=i/w;for yy in y.saturating_sub(1)..=(y+1).min(h-1){for xx in x.saturating_sub(1)..=(x+1).min(w-1){let j=yy*w+xx;if original[j]!=255&&original[j]!=color{neighbors.insert(j);}}}}
  let mut votes=vec![0usize;palette.len()];for j in neighbors{votes[original[j] as usize]+=1;}let mut target=0;for j in 1..votes.len(){if votes[j]>votes[target]{target=j;}}if votes[target]==0{continue;}let distance=(0..3).map(|j|(palette[color as usize][j] as i32-palette[target][j] as i32).pow(2)).sum::<i32>();if distance>1225{continue;}for i in queue{labels[i]=target as u8;}
 }
}
