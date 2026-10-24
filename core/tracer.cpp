// SPDX-License-Identifier: GPL-2.0-or-later
// Local color segmentation and Bezier reconstruction. No network or image codecs.
#include <vector>
#include <array>
#include <algorithm>
#include <string>
#include <sstream>
#include <iomanip>
#include <cmath>
#include <cstdlib>
#include <climits>
#include "potracelib.h"

using Color=std::array<double,3>;
static std::string result;
static int paths=0;
static double distance(const Color&a,const Color&b){double d=0;for(int c=0;c<3;c++)d+=(a[c]-b[c])*(a[c]-b[c]);return d;}

extern "C" int trace_paths(){return paths;}
extern "C" const char* trace_rgba(const unsigned char* rgba,int w,int h,int colors,int detail,int speckle,int polygon){
 result.clear();paths=0;
 if(!rgba||w<1||h<1||w>4096||h>4096||static_cast<long long>(w)*h>8000000||colors<2||colors>128||detail<0||detail>2||speckle<0||speckle>100)return nullptr;
 try {
 // A 5-bit histogram bounds palette fitting independently of image dimensions.
 std::vector<int> hist(32768,0);std::vector<Color> sums(32768,Color{0,0,0});
 for(int i=0;i<w*h;i++)if(rgba[4*i+3]>=128){int k=(rgba[4*i]>>3)*1024+(rgba[4*i+1]>>3)*32+(rgba[4*i+2]>>3);hist[k]++;for(int c=0;c<3;c++)sums[k][c]+=rgba[4*i+c];}
 std::vector<int> bins;for(int i=0;i<32768;i++)if(hist[i]){bins.push_back(i);for(int c=0;c<3;c++)sums[i][c]/=hist[i];}
 std::vector<Color> palette;
 if(!bins.empty()){
 int first=*std::max_element(bins.begin(),bins.end(),[&](int x,int y){return hist[x]<hist[y];});palette.push_back(sums[first]);
 while(palette.size()<static_cast<size_t>(colors)&&palette.size()<bins.size()){
 double best=-1;int chosen=first;
 for(int b:bins){double d=1e30;for(auto&p:palette)d=std::min(d,distance(sums[b],p));double score=d*std::sqrt(hist[b]);if(score>best){best=score;chosen=b;}}
 if(best<.01)break;palette.push_back(sums[chosen]);
 }
 for(int iteration=0;iteration<16;iteration++){
 std::vector<Color> acc(palette.size(),Color{0,0,0});std::vector<double> weights(palette.size(),0);double movement=0;
 for(int b:bins){int label=0;double best=1e30;for(size_t k=0;k<palette.size();k++){double d=distance(sums[b],palette[k]);if(d<best){best=d;label=k;}}weights[label]+=hist[b];for(int c=0;c<3;c++)acc[label][c]+=sums[b][c]*hist[b];}
 for(size_t k=0;k<palette.size();k++)if(weights[k]){for(int c=0;c<3;c++)acc[k][c]/=weights[k];movement+=distance(acc[k],palette[k]);palette[k]=acc[k];}if(movement<.1)break;
 }
 }
 std::vector<int> labels(w*h,-1);std::vector<int> counts(palette.size(),0);
 for(int i=0;i<w*h;i++)if(rgba[4*i+3]>=128){Color p{double(rgba[4*i]),double(rgba[4*i+1]),double(rgba[4*i+2])};double best=1e30;for(size_t k=0;k<palette.size();k++){double d=distance(p,palette[k]);if(d<best){best=d;labels[i]=k;}}if(labels[i]>=0)counts[labels[i]]++;}
 std::vector<int> order;for(size_t k=0;k<palette.size();k++)if(counts[k])order.push_back(k);std::stable_sort(order.begin(),order.end(),[&](int x,int y){return counts[x]>counts[y];});
 std::ostringstream out;out.imbue(std::locale::classic());out<<std::fixed<<std::setprecision(3);out<<"<svg xmlns=\"http://www.w3.org/2000/svg\" width=\""<<w<<"\" height=\""<<h<<"\" viewBox=\"0 0 "<<w<<" "<<h<<"\">";
 int bits=sizeof(potrace_word)*CHAR_BIT,dy=(w+bits-1)/bits;
 std::vector<potrace_word> map(static_cast<size_t>(dy)*h);
 auto* param=potrace_param_default();if(!param)return nullptr;param->turdsize=speckle;param->alphamax=polygon?0:1.;param->opttolerance=detail==2?.12:detail==1?.24:.48;
 for(int label:order){
 // A full silhouette below the interior regions prevents transparent seams
 // between independently fitted Bezier boundaries.
 std::fill(map.begin(),map.end(),0);for(int y=0;y<h;y++)for(int x=0;x<w;x++)if(label==order.front()?labels[y*w+x]>=0:labels[y*w+x]==label)map[y*dy+x/bits]|=static_cast<potrace_word>(1)<<(bits-1-x%bits);
 potrace_bitmap_t bitmap{w,h,dy,map.data()};auto* state=potrace_trace(param,&bitmap);if(!state||state->status!=POTRACE_STATUS_OK){if(state)potrace_state_free(state);potrace_param_free(param);return nullptr;}
 if(state->plist){char hex[8];snprintf(hex,sizeof(hex),"#%02x%02x%02x",int(std::round(palette[label][0])),int(std::round(palette[label][1])),int(std::round(palette[label][2])));out<<"<path fill=\""<<hex<<"\" fill-rule=\"nonzero\" d=\"";
 for(auto*p=state->plist;p;p=p->next){auto&curve=p->curve;auto start=curve.c[curve.n-1][2];out<<"M"<<start.x<<","<<start.y;
 for(int j=0;j<curve.n;j++){auto*c=curve.c[j];if(curve.tag[j]==POTRACE_CORNER)out<<"L"<<c[1].x<<","<<c[1].y<<" "<<c[2].x<<","<<c[2].y;else out<<"C"<<c[0].x<<","<<c[0].y<<" "<<c[1].x<<","<<c[1].y<<" "<<c[2].x<<","<<c[2].y;}out<<"Z";paths++;}out<<"\"/>";}
 potrace_state_free(state);
 }
 potrace_param_free(param);out<<"</svg>";result=out.str();return result.c_str();
 }catch(...){result.clear();return nullptr;}
}
