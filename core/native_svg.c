/* MIT-licensed SVG adapter. The linked Potrace library is GPL-2.0-or-later. */
#include "potracelib.h"
#include <stdlib.h>
#include <stdio.h>
#include <stdarg.h>
#include <stdint.h>
typedef struct {char *data;size_t used,capacity;int failed;} buffer;
static void append(buffer *b,const char *format,...){
 if(b->failed)return;
 for(;;){
  if(b->capacity-b->used<256){size_t capacity=b->capacity?b->capacity*2:1024;char *p=realloc(b->data,capacity);if(!p){b->failed=1;return;}b->data=p;b->capacity=capacity;}
  va_list args;va_start(args,format);int n=vsnprintf(b->data+b->used,b->capacity-b->used,format,args);va_end(args);
  if(n<0){b->failed=1;return;}if((size_t)n<b->capacity-b->used){b->used+=n;return;}
  size_t capacity=b->used+(size_t)n+256;char *p=realloc(b->data,capacity);if(!p){b->failed=1;return;}b->data=p;b->capacity=capacity;
 }
}
__declspec(dllexport) void doctor_free(void *p){free(p);}
__declspec(dllexport) const char *doctor_version(void){return potrace_version();}
__declspec(dllexport) char *doctor_svg(const potrace_bitmap_t *bitmap,double tolerance,double alpha){
 potrace_param_t *param=potrace_param_default();if(!param)return NULL;
 param->turdsize=0;param->opttolerance=tolerance;param->alphamax=alpha;
 potrace_state_t *state=potrace_trace(param,bitmap);potrace_param_free(param);
 if(!state)return NULL;if(state->status){potrace_state_free(state);return NULL;}
 buffer b={0};append(&b,"");
 for(potrace_path_t *p=state->plist;p;p=p->next){
  potrace_curve_t *c=&p->curve;if(!c->n)continue;potrace_dpoint_t start=c->c[c->n-1][2];append(&b,"M%.3f %.3f",start.x,start.y);
  for(int j=0;j<c->n;j++){potrace_dpoint_t *v=c->c[j];if(c->tag[j]==POTRACE_CORNER)append(&b,"L%.3f %.3f %.3f %.3f",v[1].x,v[1].y,v[2].x,v[2].y);else append(&b,"C%.3f %.3f %.3f %.3f %.3f %.3f",v[0].x,v[0].y,v[1].x,v[1].y,v[2].x,v[2].y);}append(&b,"Z");
 }
 potrace_state_free(state);if(b.failed){free(b.data);return NULL;}return b.data;
}
