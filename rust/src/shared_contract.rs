// Every edge, including the unpainted exterior face, has two reversed owners.
use std::collections::HashMap;
pub fn verify(faces:&[(i32,String)])->bool{
 let mut edges:HashMap<Vec<i64>,Vec<(i32,i8)>>=HashMap::new();
 for (owner,data) in faces{
  let text=data.replace('M'," M ").replace('L'," L ").replace('C'," C ").replace('Z'," Z ");
  let tokens:Vec<_>=text.split_whitespace().collect();let mut i=0;let mut cmd="";let mut p=[0i64;2];let mut start=p;
  while i<tokens.len(){if matches!(tokens[i],"M"|"L"|"C"|"Z"){cmd=tokens[i];i+=1;}
   if cmd=="Z"{if p!=start{let a=vec![0,p[0],p[1],start[0],start[1]];let b=vec![0,start[0],start[1],p[0],p[1]];let direction=if a<=b{1}else{-1};edges.entry(a.min(b)).or_default().push((*owner,direction));}p=start;cmd="";continue;}
   let n=if cmd=="C"{6}else{2};if i+n>tokens.len(){return false;}
   let mut v=Vec::new();for t in &tokens[i..i+n]{let Ok(x)=t.parse::<f64>() else{return false;};v.push((x*10000.).round() as i64);}i+=n;
   if cmd=="M"{p=[v[0],v[1]];start=p;cmd="L";continue;}
   let mut direction=1;let key=if cmd=="L"{if p==[v[0],v[1]]{None}else{let a=vec![0,p[0],p[1],v[0],v[1]];let b=vec![0,v[0],v[1],p[0],p[1]];direction=if a<=b{1}else{-1};Some(a.min(b))}}
   else if cmd=="C"{if v.chunks_exact(2).all(|q|q==p){None}else{let a=vec![1,p[0],p[1],v[0],v[1],v[2],v[3],v[4],v[5]];let b=vec![1,v[4],v[5],v[2],v[3],v[0],v[1],p[0],p[1]];direction=if a<=b{1}else{-1};Some(a.min(b))}}else{return false;};
   if let Some(k)=key{edges.entry(k).or_default().push((*owner,direction));}p=[v[n-2],v[n-1]];
  }
 }
 edges.values().all(|v|v.len()==2&&v[0].0!=v[1].0&&v[0].1+v[1].1==0)
}
