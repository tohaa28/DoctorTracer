/* Integer CPU reference/production fallback for the OpenCL mode filter.
 * Copyright (c) 2026 DoctorTracer contributors. MIT licensed. */
#include <stdint.h>
#define MIN(a,b) ((a)<(b)?(a):(b))
#define MAX(a,b) ((a)>(b)?(a):(b))
__declspec(dllexport) void doctor_modes(const uint8_t *src,uint8_t *dst,
    int w,int h,int radius,int range2,int iterations,int first,int last) {
    for(int oy=first;oy<last;oy++)for(int ox=0;ox<w;ox++) {
        int pos=(oy*w+ox)*4;
        for(int c=0;c<4;c++)dst[pos+c]=src[pos+c];
        if(src[pos+3]<128)continue;
        int x=ox,y=oy,r=src[pos],g=src[pos+1],b=src[pos+2];
        for(int k=0;k<iterations;k++) {
            int sx=0,sy=0,sr=0,sg=0,sb=0,n=0;
            for(int yy=MAX(0,y-radius);yy<=MIN(h-1,y+radius);yy++)
                for(int xx=MAX(0,x-radius);xx<=MIN(w-1,x+radius);xx++) {
                    const uint8_t *v=src+(yy*w+xx)*4;
                    if(v[3]<128)continue;
                    int dr=v[0]-r,dg=v[1]-g,db=v[2]-b;
                    if(dr*dr+dg*dg+db*db>range2)continue;
                    n++;sx+=xx;sy+=yy;sr+=v[0];sg+=v[1];sb+=v[2];
                }
            if(!n)break;
            int nx=(sx+n/2)/n,ny=(sy+n/2)/n;
            int nr=(sr+n/2)/n,ng=(sg+n/2)/n,nb=(sb+n/2)/n;
            int done=nx==x&&ny==y&&nr==r&&ng==g&&nb==b;
            x=nx;y=ny;r=nr;g=ng;b=nb;
            if(done)break;
        }
        dst[pos]=r;dst[pos+1]=g;dst[pos+2]=b;
    }
}
