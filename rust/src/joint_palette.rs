// SPDX-License-Identifier: MIT
pub fn narrow(pixels:&[&[u8]])->bool{
 if pixels.len()<2{return true;}let sample:Vec<_>=pixels.iter().step_by((pixels.len()/60000).max(1)).collect();let mut mean=[0.;3];for p in &sample{for j in 0..3{mean[j]+=p[j] as f64;}}for j in 0..3{mean[j]/=sample.len() as f64;}
 let mut cov=[[0.;3];3];for p in sample{for i in 0..3{for j in 0..3{cov[i][j]+=(p[i] as f64-mean[i])*(p[j] as f64-mean[j]);}}}let mut v=[1.;3];for _ in 0..20{let next=std::array::from_fn::<_,3,_>(|i|(0..3).map(|j|cov[i][j]*v[j]).sum::<f64>());let n=next.iter().map(|v|v*v).sum::<f64>().sqrt();if n<1e-12{return true;}v=next.map(|v|v/n);}
 let largest=(0..3).map(|i|(0..3).map(|j|v[i]*cov[i][j]*v[j]).sum::<f64>()).sum::<f64>();largest>=0.92*(cov[0][0]+cov[1][1]+cov[2][2])
}
fn energy(a:&[u8],labels:&[u8],palette:&[[u8;3]],w:usize,h:usize)->i64{
 let mut sum=0;for i in 0..w*h{if a[4*i+3]<128{continue;}let c=palette[labels[i] as usize];for j in 0..3{sum+=(a[4*i+j] as i64-c[j] as i64).pow(2);}if i>=w&&a[4*(i-w)+3]>=128&&labels[i]!=labels[i-w]{sum+=700;}if i%w>0&&a[4*(i-1)+3]>=128&&labels[i]!=labels[i-1]{sum+=700;}}sum
}
pub fn propose(a:&[u8],labels:&[u8],palette:&[[u8;3]],w:usize,h:usize)->Vec<[u8;3]>{
 let mut count=vec![0i64;palette.len()];let mut sums=vec![[0i64;3];palette.len()];
  for i in 0..w*h{if a[4*i+3]<128{continue;}let c=labels[i];if (i>=w&&labels[i-w]!=c)||(i+w<w*h&&labels[i+w]!=c)||(i%w>0&&labels[i-1]!=c)||(i%w+1<w&&labels[i+1]!=c){continue;}count[c as usize]+=1;for j in 0..3{sums[c as usize][j]+=a[4*i+j] as i64;}}
  let mut proposed=palette.to_vec();for c in 0..palette.len(){if count[c]<16{continue;}let candidate=std::array::from_fn::<_,3,_>(|j|{let mean=(sums[c][j]+count[c]/2)/count[c];(palette[c][j] as i64+(mean-palette[c][j] as i64).clamp(-6,6)) as u8});let(mut before,mut after)=(0i64,0i64);for i in 0..w*h{if a[4*i+3]<128||labels[i] as usize!=c{continue;}for j in 0..3{before+=(a[4*i+j] as i64-palette[c][j] as i64).pow(2);after+=(a[4*i+j] as i64-candidate[j] as i64).pow(2);}}if after<before{proposed[c]=candidate;}}
 proposed
}
pub fn choose(a:&[u8],old:&[u8],candidate:&[u8],palette:&[[u8;3]],w:usize,h:usize)->Vec<u8>{if energy(a,candidate,palette,w,h)<energy(a,old,palette,w,h){candidate.to_vec()}else{old.to_vec()}}
pub fn refine(a:&[u8],labels:&mut Vec<u8>,palette:&mut Vec<[u8;3]>,w:usize,h:usize){
 for _ in 0..3{let proposed=propose(a,labels,palette,w,h);if *palette==proposed{break;}*palette=proposed;let candidate=crate::desktop_filters::segment(a,w,h,palette,700,false,3);*labels=choose(a,labels,&candidate,palette,w,h);}
}
