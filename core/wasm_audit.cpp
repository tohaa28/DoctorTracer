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
struct Item{Paths paths;IntRect bounds;};static std::vector<Item> seen;static std::map<std::pair<cInt,cInt>,std::vector<size_t>> grid;static int pairs;
static Paths covered;static Path rect;static std::string partition_text;
extern "C"{
void partition_start(double w,double h){covered.clear();rect={IntPoint(0,0),IntPoint((cInt)(w*1e7),0),IntPoint((cInt)(w*1e7),(cInt)(h*1e7)),IntPoint(0,(cInt)(h*1e7))};}
const char* partition_add(const double *data,int length){try{Paths paths;int i=0;while(i<length){int n=(int)data[i++];if(n<3||i+n*2>length)return NULL;Path path;for(int j=0;j<n;j++){path.push_back(IntPoint((cInt)data[i],(cInt)data[i+1]));i+=2;}paths.push_back(path);}Clipper local;local.AddPaths(paths,ptSubject,true);local.AddPath(rect,ptClip,true);Paths inside;local.Execute(ctIntersection,inside,pftNonZero,pftNonZero);Clipper clip;clip.AddPaths(inside,ptSubject,true);clip.AddPaths(covered,ptClip,true);Paths visible;clip.Execute(ctDifference,visible,pftNonZero,pftNonZero);covered.insert(covered.end(),visible.begin(),visible.end());partition_text.clear();char point[100];for(const auto &path:visible){for(size_t j=0;j<path.size();j++){snprintf(point,sizeof(point),"%c%.7f %.7f ",j?'L':'M',path[j].X/1e7,path[j].Y/1e7);partition_text+=point;}partition_text+="Z ";}return partition_text.c_str();}catch(...){return NULL;}}
void audit_start(){seen.clear();grid.clear();pairs=0;}
int audit_pairs(){return pairs;}
double audit_add(const double *data,int length){try{
 Paths paths;int i=0;while(i<length){int n=(int)data[i++];if(n<3||i+n*2>length)return -1;Path path;path.reserve(n);for(int j=0;j<n;j++){path.push_back(IntPoint((cInt)data[i],(cInt)data[i+1]));i+=2;}paths.push_back(path);}if(paths.empty())return 0;
 Clipper measure;measure.AddPaths(paths,ptSubject,true);IntRect b=measure.GetBounds();const double span=128.*10000000.;std::set<size_t> candidates;std::vector<std::pair<cInt,cInt>> keys;
 for(cInt y=(cInt)floor(b.top/span);y<=(cInt)floor(b.bottom/span);y++)for(cInt x=(cInt)floor(b.left/span);x<=(cInt)floor(b.right/span);x++){auto key=std::make_pair(x,y);keys.push_back(key);auto found=grid.find(key);if(found!=grid.end())candidates.insert(found->second.begin(),found->second.end());}
 double maxArea=0;for(auto j:candidates){const auto &other=seen[j];const auto &c=other.bounds;if(b.left>=c.right||b.right<=c.left||b.top>=c.bottom||b.bottom<=c.top)continue;Clipper clip;clip.AddPaths(paths,ptSubject,true);clip.AddPaths(other.paths,ptClip,true);Paths intersection;clip.Execute(ctIntersection,intersection,pftNonZero,pftNonZero);pairs++;double area=0;for(const auto &p:intersection)area+=Area(p);area=fabs(area)/1e14;maxArea=std::max(maxArea,area);if(area>.0001)return area;}
 size_t id=seen.size();seen.push_back(Item{std::move(paths),b});for(const auto &key:keys)grid[key].push_back(id);return maxArea;
 }catch(...){return -1;}}
}
