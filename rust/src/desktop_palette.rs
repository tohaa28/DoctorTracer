// SPDX-License-Identifier: Apache-2.0
// OpenCV k-means++ control flow and RNG semantics, adapted from OpenCV core/kmeans.cpp
// (OpenCV team, https://github.com/opencv/opencv). Desktop uses seed 27, 3 attempts,
// 3 PP trials, 35 iterations, epsilon 0.2, and cluster medians rather than centers.
struct Rng(u64);impl Rng{fn next(&mut self)->u32{self.0=(self.0 as u32 as u64)*4164903690+(self.0>>32);self.0 as u32}fn double(&mut self)->f64{let a=self.next() as u64;((a<<32)|self.next() as u64) as f64*5.421010862427522e-20}}
fn d(a:&[f32;3],b:&[f32;3])->f32{let x=a[0]-b[0];let y=a[1]-b[1];let z=a[2]-b[2];(x*x+y*y)+z*z}
fn med(mut v:Vec<u8>)->u8{v.sort_unstable();let n=v.len();if n%2==1{v[n/2]}else{((v[n/2-1] as u16+v[n/2] as u16)/2) as u8}}
fn legacy(a:&[u8],w:usize,h:usize,count:usize,photo:bool)->Vec<[u8;3]>{legacy_attempts(a,w,h,count,photo,3)}
fn legacy_attempts(a:&[u8],w:usize,h:usize,count:usize,photo:bool,attempts:usize)->Vec<[u8;3]>{
 let all:Vec<[u8;3]>=a.chunks_exact(4).filter(|p|p[3]>=128).map(|p|[p[0],p[1],p[2]]).collect();if all.is_empty(){return vec![[255;3]];}
 if count==1{return vec![std::array::from_fn(|c|med(all.iter().map(|p|p[c]).collect()))];}
 if !photo&&count==0{
  let mut flat=Vec::new();for y in 0..h{for x in 0..w{let i=4*(y*w+x);if a[i+3]<128{continue;}let mut lo=[255u8;3];let mut hi=[0u8;3];for yy in y.saturating_sub(1)..=(y+1).min(h-1){for xx in x.saturating_sub(1)..=(x+1).min(w-1){for c in 0..3{lo[c]=lo[c].min(a[4*(yy*w+xx)+c]);hi[c]=hi[c].max(a[4*(yy*w+xx)+c]);}}}if (0..3).map(|c|hi[c]-lo[c]).max().unwrap()<22{flat.push([a[i],a[i+1],a[i+2]]);}}}
  let values=if flat.len()>64{&flat}else{&all};let samples:Vec<_>=values.iter().step_by((values.len()/60000).max(1)).collect();let mut bins=vec![Vec::<[u8;3]>::new();32768];for &&p in &samples{let key=(p[0] as usize/8)*1024+(p[1] as usize/8)*32+p[2] as usize/8;bins[key].push(p);}
  let mut order:Vec<_>=(0..32768).filter(|&k|!bins[k].is_empty()).collect();order.sort_by_key(|&k|std::cmp::Reverse(bins[k].len()));let mut out=Vec::<[u8;3]>::new();for &k in order.iter().take(128){if (bins[k].len() as f64)<4f64.max(samples.len() as f64*0.0015){break;}let color=std::array::from_fn(|c|med(bins[k].iter().map(|p|p[c]).collect()));if out.iter().all(|p|(0..3).map(|c|(p[c] as f64-color[c] as f64).powi(2)).sum::<f64>()>576.){out.push(color);}if out.len()>=24{break;}}
  if out.is_empty(){out.push(std::array::from_fn(|c|med(samples.iter().map(|p|p[c]).collect())));}return out;
 }
 let pixels:Vec<[f32;3]>=all.iter().step_by((all.len()/60000).max(1)).map(|p|p.map(|v|v as f32)).collect();
 let unique:std::collections::BTreeSet<_>=pixels.iter().map(|p|p.map(|v|v as u8)).collect();let k=count.max(2).min(64).min(unique.len());let n=pixels.len();let mut rng=Rng(27);let mut best=f64::MAX;let mut best_labels=vec![0usize;n];
 for _ in 0..attempts{
  let first=rng.next() as usize%n;let mut centers=vec![pixels[first]];let mut dist:Vec<f32>=pixels.iter().map(|p|d(p,&pixels[first])).collect();let mut total: f64=dist.iter().map(|&v|v as f64).sum();
  while centers.len()<k{let mut best_sum=f64::MAX;let mut best_center=0;let mut best_dist=Vec::new();for _ in 0..3{let mut p=rng.double()*total;let mut ci=0;while ci<n-1{p-=dist[ci] as f64;if p<=0.{break;}ci+=1;}let next:Vec<f32>=pixels.iter().zip(&dist).map(|(p,&old)|old.min(d(p,&pixels[ci]))).collect();let mut s=0f64;let mut i=0;while i+7<n{let mut sum=next[i];for v in &next[i+1..i+8]{sum+=v;}s+=sum as f64;i+=8;}for &v in &next[i..]{s+=v as f64;}if s<best_sum{best_sum=s;best_center=ci;best_dist=next;}}centers.push(pixels[best_center]);dist=best_dist;total=best_sum;}
  let mut labels=vec![0usize;n];let mut iteration=0;
  loop{let mut shift=if iteration==0{f64::MAX}else{0.};if iteration>0{let old=centers.clone();centers.fill([0.;3]);let mut counts=vec![0usize;k];for (i,p) in pixels.iter().enumerate(){let c=labels[i];counts[c]+=1;for j in 0..3{centers[c][j]+=p[j];}}
    for c in 0..k{if counts[c]>0{continue;}let mut maxc=0;for j in 1..k{if counts[j]>counts[maxc]{maxc=j;}}let scale=1f32/counts[maxc] as f32;let mean=centers[maxc].map(|v|v*scale);let mut far=0;let mut far_dist=0.;for i in 0..n{if labels[i]!=maxc{continue;}let dd=d(&pixels[i],&mean);if dd>=far_dist{far_dist=dd;far=i;}}counts[maxc]-=1;counts[c]+=1;labels[far]=c;for j in 0..3{centers[maxc][j]-=pixels[far][j];centers[c][j]+=pixels[far][j];}}
    for c in 0..k{let scale=1f32/counts[c] as f32;for j in 0..3{centers[c][j]*=scale;}let movement=(0..3).map(|j|(centers[c][j]-old[c][j]) as f64).map(|v|v*v).sum::<f64>();shift=shift.max(movement);}
   }
   iteration+=1;if iteration==35||shift<=0.04{let compact=pixels.iter().enumerate().map(|(i,p)|d(p,&centers[labels[i]]) as f64).sum::<f64>();if compact<best{best=compact;best_labels=labels.clone();}break;}
   for(i,p)in pixels.iter().enumerate(){let mut min=f32::MAX;for(c,center)in centers.iter().enumerate(){let dd=d(p,center);if dd<min{min=dd;labels[i]=c;}}}
  }
 }
 let mut buckets=vec![Vec::<[u8;3]>::new();k];for(i,p)in pixels.iter().enumerate(){buckets[best_labels[i]].push(p.map(|v|v as u8));}
 buckets.into_iter().filter(|b|!b.is_empty()).map(|b|std::array::from_fn(|c|med(b.iter().map(|p|p[c]).collect()))).collect()
}

// Fixed limits are maxima, not a request to quantize antialias mixtures into inks.
pub fn find(a:&[u8],w:usize,h:usize,count:usize,photo:bool)->Vec<[u8;3]>{
 if count<=1||count>24{return legacy(a,w,h,count,photo);}
 let interior=legacy(a,w,h,0,false);
 let all:Vec<_>=a.chunks_exact(4).filter(|p|p[3]>=128).collect();
 if all.is_empty(){return vec![[255;3]];}
 if interior.len()<=count{
  let sample:Vec<_>=all.iter().step_by((all.len()/60000).max(1)).collect();
  let good=sample.iter().filter(|p|interior.iter().any(|c|(0..3).map(|j|(p[j] as i32-c[j] as i32).pow(2)).sum::<i32>()<=576)).count();
  if good as f64/sample.len() as f64>=0.96{return interior;}
  if good as f64/sample.len() as f64>=0.75{
   let explained=sample.iter().filter(|p|{
    if interior.iter().any(|c|(0..3).map(|j|(p[j] as i32-c[j] as i32).pow(2)).sum::<i32>()<=576){return true;}
    for i in 0..interior.len(){for j in i+1..interior.len(){let left=interior[i].map(|v|v as f64);let d=std::array::from_fn::<_,3,_>(|k|interior[j][k] as f64-left[k]);let den=d.iter().map(|v|v*v).sum::<f64>();if den==0.{continue;}let t=((0..3).map(|k|(p[k] as f64-left[k])*d[k]).sum::<f64>()/den).clamp(0.,1.);let error=(0..3).map(|k|(p[k] as f64-left[k]-t*d[k]).powi(2)).sum::<f64>();if error<=64.{return true;}}}false
   }).count();if explained as f64/sample.len() as f64>=0.995{return interior;}
  }
 }
 let mut counts=vec![0u32;32768];let mut sums=vec![[0u64;3];32768];
 for p in all.iter().step_by((all.len()/60000).max(1)){
  let k=(p[0] as usize/8)*1024+(p[1] as usize/8)*32+p[2] as usize/8;counts[k]+=1;for j in 0..3{sums[k][j]+=p[j] as u64;}
 }
 let weights:Vec<f64>=counts.iter().map(|&n|(n as f64).powf(0.75)).collect();let total:f64=weights.iter().sum();let mut sampled=Vec::new();
 for k in 0..32768{if counts[k]==0{continue;}let n=(weights[k]*60000./total).round().max(1.) as usize;let c=std::array::from_fn::<_,3,_>(|j|((sums[k][j] as f64/counts[k] as f64).round()) as u8);for _ in 0..n{sampled.extend_from_slice(&[c[0],c[1],c[2],255]);}}
 legacy_attempts(&sampled,sampled.len()/4,1,count,true,5)
}
