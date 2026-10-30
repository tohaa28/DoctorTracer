/* SPDX-License-Identifier: GPL-2.0-or-later
 * Potrace 1.16 mask adapter: same tolerance/alpha as desktop native_trace.
 */
#include "potracelib.h"
#include <stdint.h>
#include <stdlib.h>
#include <stdio.h>
#include <stdarg.h>
static char *text;static size_t used,capacity;
static void put(const char *fmt,...){for(;;){if(capacity-used<256){capacity=capacity?capacity*2:4096;text=realloc(text,capacity);if(!text)abort();}va_list args;va_start(args,fmt);int n=vsnprintf(text+used,capacity-used,fmt,args);va_end(args);if(n>=0&&(size_t)n<capacity-used){used+=n;return;}capacity=used+(size_t)n+256;text=realloc(text,capacity);if(!text)abort();}}
const char *trace_mask(const uint8_t *mask,int w,int h,double tolerance,double alpha){
 if(!mask||w<1||h<1||w>8192||h>8192||(uint64_t)w*h>32000000)return NULL;used=0;put("");int stride=(w+31)/32;potrace_word *map=calloc((size_t)stride*h,sizeof(potrace_word));if(!map)return NULL;
 for(int y=0;y<h;y++)for(int x=0;x<w;x++)if(mask[y*w+x])map[(h-1-y)*stride+x/32]|=(potrace_word)1<<(31-x%32);
 potrace_bitmap_t bitmap={w,h,stride,map};potrace_param_t *param=potrace_param_default();param->turdsize=0;param->opttolerance=tolerance;param->alphamax=alpha;potrace_state_t *state=potrace_trace(param,&bitmap);potrace_param_free(param);free(map);if(!state||state->status){if(state)potrace_state_free(state);return NULL;}
 for(potrace_path_t *p=state->plist;p;p=p->next){potrace_curve_t *c=&p->curve;if(!c->n)continue;potrace_dpoint_t first=c->c[c->n-1][2];put("M%.2f %.2f",first.x,h-first.y);
  for(int j=0;j<c->n;j++){potrace_dpoint_t *v=c->c[j];if(c->tag[j]==POTRACE_CORNER)put("L%.2f %.2f %.2f %.2f",v[1].x,h-v[1].y,v[2].x,h-v[2].y);else put("C%.2f %.2f %.2f %.2f %.2f %.2f",v[0].x,h-v[0].y,v[1].x,h-v[1].y,v[2].x,h-v[2].y);}put("Z");
 }potrace_state_free(state);return text;
}
