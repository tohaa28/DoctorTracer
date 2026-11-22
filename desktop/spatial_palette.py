"""Experimental spatial color assignment for fixed-palette photographs.

Integer RGB data cost plus a four-neighbor Potts penalty. Checkerboard updates
keep each phase independent and make CPU and OpenCL results deterministic.
This deliberately changes segmentation; it is not an equivalent faster tracer.
"""
import threading
import time
import numpy as np
import accelerator

SOURCE = r'''
__kernel void spatial(__global const uchar4 *rgba,
 __global const uchar4 *palette, int count, __global const uchar *labels,
 __global uchar *result, int w, int h, int strength, int phase) {
 int i=get_global_id(0); if(i>=w*h)return;
 int x=i%w, y=i/w; uchar4 pixel=rgba[i];
 if(pixel.w<128){result[i]=255;return;}
 if(((x+y)&1)!=phase){result[i]=labels[i];return;}
 int left=(x>0 && rgba[i-1].w>127)?labels[i-1]:255;
 int right=(x+1<w && rgba[i+1].w>127)?labels[i+1]:255;
 int top=(y>0 && rgba[i-w].w>127)?labels[i-w]:255;
 int bottom=(y+1<h && rgba[i+w].w>127)?labels[i+w]:255;
 int best=2147483647; uchar chosen=labels[i];
 for(int c=0;c<count;c++) {
  int3 delta=convert_int3(pixel.xyz)-convert_int3(palette[c].xyz);
  int energy=delta.x*delta.x+delta.y*delta.y+delta.z*delta.z;
  energy+=strength*((left!=255 && left!=c)+(right!=255 && right!=c)
                   +(top!=255 && top!=c)+(bottom!=255 && bottom!=c));
  if(energy<best){best=energy;chosen=c;}
 }
 result[i]=chosen;
}
'''
_kernel = None
_context = None
_lock = threading.Lock()


def assign_cpu(a, palette, strength=700, iterations=2):
    labels = accelerator.assign_cpu(a, palette, False, 0)
    rgb = a[:, :, :3].astype(np.int32)
    visible = a[:, :, 3] >= 128
    parity = np.indices(labels.shape).sum(axis=0) & 1
    for _ in range(iterations):
        for phase in (0, 1):
            padded = np.pad(labels, 1, constant_values=255)
            neighbors = (padded[:-2, 1:-1], padded[2:, 1:-1],
                         padded[1:-1, :-2], padded[1:-1, 2:])
            best = np.full(labels.shape, np.iinfo(np.int32).max, np.int32)
            result = labels.copy()
            active = visible & (parity == phase)
            for i, color in enumerate(palette):
                delta = rgb - np.asarray(color, dtype=np.int32)
                energy = np.sum(delta * delta, axis=2, dtype=np.int32)
                for neighbor in neighbors:
                    energy += strength * ((neighbor != 255) & (neighbor != i))
                take = active & (energy < best)
                best[take] = energy[take]
                result[take] = i
            labels = result
    return labels


def assign_gpu(a, palette, strength=700, iterations=2):
    global _kernel, _context
    # No intermediate label download: nearest and every spatial phase share VRAM.
    with _lock:
        cl, ctx, queue, nearest, _, _, name = accelerator.gpu_runtime()
        if _kernel is None or _context is not ctx:
            program = cl.Program(ctx, SOURCE).build(options=['-cl-std=CL1.2'])
            _kernel = cl.Kernel(program, 'spatial')
            _context = ctx
        rgba = np.ascontiguousarray(a, dtype=np.uint8)
        h, w = rgba.shape[:2]
        n = w*h
        pal = np.zeros((len(palette), 4), np.uint8)
        pal[:, :3] = palette
        f = cl.mem_flags
        src = cl.Buffer(ctx, f.READ_ONLY | f.COPY_HOST_PTR, hostbuf=rgba)
        inks = cl.Buffer(ctx, f.READ_ONLY | f.COPY_HOST_PTR, hostbuf=pal)
        labels = cl.Buffer(ctx, f.READ_WRITE, n)
        other = cl.Buffer(ctx, f.READ_WRITE, n)
        distances = cl.Buffer(ctx, f.READ_WRITE, n*4)
        nearest(queue, (n,), None, src, inks, np.int32(len(pal)), np.int32(n), labels, distances)
        for _ in range(iterations):
            for phase in (0, 1):
                _kernel(queue, (n,), None, src, inks, np.int32(len(pal)), labels,
                        other, np.int32(w), np.int32(h), np.int32(strength), np.int32(phase))
                labels, other = other, labels
        result = np.empty((h, w), np.uint8)
        cl.enqueue_copy(queue, result, labels).wait()
        result[rgba[:, :, 3] < 128] = 255
        return result, name


def assign(a, palette, backend='auto', strength=700, iterations=2):
    strength = int(strength)
    iterations = int(iterations)
    if not 0 <= strength <= 100000 or not 0 <= iterations <= 20:
        raise ValueError('Spatial strength must be 0..100000; iterations 0..20')
    if not 1 <= len(palette) <= 64:
        raise ValueError('Spatial assignment requires 1..64 palette colors')
    started = time.perf_counter()
    fallback = None
    gpu = backend == 'gpu' or (backend == 'auto' and a.shape[0]*a.shape[1] >= 500000)
    if gpu:
        try:
            labels, name = assign_gpu(a, palette, strength, iterations)
            return labels, {'compute': 'OpenCL GPU', 'device': name,
                            'segmentation': 'spatial-experimental',
                            'assignment_seconds': time.perf_counter()-started}
        except Exception as exc:
            fallback = str(exc)
    labels = assign_cpu(a, palette, strength, iterations)
    return labels, {'compute': 'OpenCV CPU', 'gpu_fallback': fallback,
                    'segmentation': 'spatial-experimental',
                    'assignment_seconds': time.perf_counter()-started}
