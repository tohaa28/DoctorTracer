// SPDX-License-Identifier: MIT
// Exact Clipper 6.4.2 integer intersection audit used by desktop/vector_partition.py.
#include "clipper.hpp"
#include <vector>
#include <map>
#include <set>
#include <cmath>
#include <string>
#include <cstdio>
using namespace ClipperLib;

using Key=std::pair<cInt,cInt>;
const cInt SPAN=1280000000LL;
struct Item{Paths paths;IntRect bounds;size_t id;};
static std::vector<Paths> originals;
static std::map<Key,std::vector<Item>> audit_tiles;
static std::map<Key,Paths> covered_tiles;
static int pairs;static Path rect;static std::string partition_text;
static int active_group=-1;static std::map<int,Paths> partition_groups;
IntRect bounds_of(const Paths &paths){IntRect b;bool first=true;for(const auto &path:paths)for(const auto &p:path){if(first){b={p.X,p.Y,p.X,p.Y};first=false;}else{b.left=std::min(b.left,p.X);b.right=std::max(b.right,p.X);b.top=std::min(b.top,p.Y);b.bottom=std::max(b.bottom,p.Y);}}return b;}
Paths decode(const double *data,int length){Paths paths;int i=0;while(i<length){int n=(int)data[i++];if(n<3||i+n*2>length)throw 1;Path p;p.reserve(n);for(int j=0;j<n;j++){p.emplace_back((cInt)data[i],(cInt)data[i+1]);i+=2;}paths.push_back(std::move(p));}return paths;}
std::map<Key,Paths> bucket(const Paths &paths){std::map<Key,Paths> result;for(const auto &p:paths){IntRect b=bounds_of(Paths{p});for(cInt y=(cInt)floor((double)b.top/SPAN);y<=(cInt)floor((double)b.bottom/SPAN);y++)for(cInt x=(cInt)floor((double)b.left/SPAN);x<=(cInt)floor((double)b.right/SPAN);x++)result[{x,y}].push_back(p);}return result;}
Path tile_rect(Key key){cInt x=key.first*SPAN,y=key.second*SPAN;return {{x,y},{x+SPAN,y},{x+SPAN,y+SPAN},{x,y+SPAN}};}
Paths intersect(const Paths &a,const Paths &b){if(a.empty()||b.empty())return {};Clipper c;c.AddPaths(a,ptSubject,true);c.AddPaths(b,ptClip,true);Paths out;c.Execute(ctIntersection,out,pftNonZero,pftNonZero);return out;}
double area_of(const Paths &paths){double sum=0;for(const auto &p:paths)sum+=Area(p);return fabs(sum)/1e14;}
extern "C"{
void partition_start(double w,double h){active_group=-1;partition_groups.clear();covered_tiles.clear();rect={{0,0},{(cInt)(w*1e7),0},{(cInt)(w*1e7),(cInt)(h*1e7)},{0,(cInt)(h*1e7)}};}
const char* partition_add(const double *data,int length){try{Paths paths=decode(data,length);partition_text.clear();char point[100];for(auto &entry:bucket(paths)){Path tile=tile_rect(entry.first);Paths clip=intersect(Paths{tile},Paths{rect});Paths inside=intersect(entry.second,clip);if(inside.empty())continue;auto &covered=covered_tiles[entry.first];Paths visible;if(covered.empty())visible=inside;else{Clipper c;c.AddPaths(inside,ptSubject,true);c.AddPaths(covered,ptClip,true);c.Execute(ctDifference,visible,pftNonZero,pftNonZero);}covered.insert(covered.end(),visible.begin(),visible.end());if(active_group>=0){auto &g=partition_groups[active_group];g.insert(g.end(),visible.begin(),visible.end());}for(const auto &path:visible){for(size_t j=0;j<path.size();j++){snprintf(point,sizeof(point),"%c%.7f %.7f ",j?'L':'M',path[j].X/1e7,path[j].Y/1e7);partition_text+=point;}partition_text+="Z ";}}return partition_text.c_str();}catch(...){return NULL;}}
void audit_start(){originals.clear();audit_tiles.clear();pairs=0;}
int audit_pairs(){return pairs;}
double audit_add(const double *data,int length){try{Paths paths=decode(data,length);size_t id=originals.size();std::map<size_t,double> areas;std::set<size_t> compared;
 for(auto &entry:bucket(paths)){Paths clipped=intersect(entry.second,Paths{tile_rect(entry.first)});if(clipped.empty())continue;IntRect b=bounds_of(clipped);auto &seen=audit_tiles[entry.first];for(const auto &other:seen){const auto &c=other.bounds;if(b.left>=c.right||b.right<=c.left||b.top>=c.bottom||b.bottom<=c.top)continue;compared.insert(other.id);areas[other.id]+=area_of(intersect(clipped,other.paths));if(areas[other.id]>.000099){double exact=area_of(intersect(paths,originals[other.id]));if(exact>.0001)return exact;}}seen.push_back({std::move(clipped),b,id});}
 double maxArea=0;for(const auto &entry:areas)maxArea=std::max(maxArea,entry.second);pairs+=(int)compared.size();originals.push_back(std::move(paths));return maxArea;
 }catch(...){return -1;}}
void partition_set_group(int group){active_group=group;}
// Stitch computational tiles before exporting. Nonzero union preserves holes
// and removes coincident internal edges, without expanding any color region.
const char* merge_paths(const double *data,int length){try{
 Paths input=decode(data,length),output;Clipper c;c.AddPaths(input,ptSubject,true);
 c.Execute(ctUnion,output,pftNonZero,pftNonZero);partition_text.clear();char point[100];
 for(const auto &path:output){for(size_t j=0;j<path.size();j++){
  snprintf(point,sizeof(point),"%c%.7f %.7f ",j?'L':'M',path[j].X/1e7,path[j].Y/1e7);partition_text+=point;
 }partition_text+="Z ";}return partition_text.c_str();
 }catch(...){return NULL;}}
double partition_verify(){audit_start();double maximum=0;for(const auto &entry:partition_groups){std::vector<double> data;for(const auto &p:entry.second){data.push_back(p.size());for(const auto &v:p){data.push_back((double)v.X);data.push_back((double)v.Y);}}double area=audit_add(data.data(),(int)data.size());if(area<0||area>.0001)return area;maximum=std::max(maximum,area);}return maximum;}

}
