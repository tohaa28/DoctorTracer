"""Alternate spatial labels and automatic colours; explicit user inks stay fixed."""
import numpy as np


def narrow_model(pixels):
    p=pixels.astype(float);p=p[::max(1,len(p)//60000)]
    if len(p)<2:return True
    p-=p.mean(0);cov=p.T@p;v=np.ones(3)
    for _ in range(20):
        v=cov@v;n=float(np.sqrt(v@v))
        if n<1e-12:return True
        v/=n
    return float(v@cov@v)>=.92*float(np.trace(cov))


def refine(a,labels,palette,backend='cpu',strength=700,iterations=2):
    from spatial_palette import assign
    palette=np.asarray(palette,np.int32);labels=labels.copy();rgb=a[:,:,:3].astype(np.int32);visible=a[:,:,3]>=128
    history=[]
    def energy(lab,inks):
        data=int(((rgb[visible].astype(np.int64)-inks[lab[visible]])**2).sum())
        boundary=int(np.count_nonzero((lab[1:]!=lab[:-1])&visible[1:]&visible[:-1])+np.count_nonzero((lab[:,1:]!=lab[:,:-1])&visible[:,1:]&visible[:,:-1]))
        return data+strength*boundary
    for _ in range(3):
        inside=visible.copy()
        inside[1:]&=labels[1:]==labels[:-1];inside[:-1]&=labels[:-1]==labels[1:]
        inside[:,1:]&=labels[:,1:]==labels[:,:-1];inside[:,:-1]&=labels[:,:-1]==labels[:,1:]
        proposed=palette.copy()
        for i in range(len(palette)):
            values=rgb[inside&(labels==i)]
            if len(values)<16:continue
            mean=(values.sum(0,dtype=np.int64)+len(values)//2)//len(values)
            candidate=palette[i]+np.clip(mean-palette[i],-6,6)
            all_values=rgb[visible&(labels==i)].astype(np.int64)
            if ((all_values-candidate)**2).sum()<((all_values-palette[i])**2).sum():proposed[i]=candidate
        if np.array_equal(proposed,palette):break
        # Each colour update lowers the complete data term for the old labels;
        # checkerboard assignment lowers data+Potts for the updated colours.
        old=energy(labels,palette)
        palette=proposed
        candidate_labels,stats=assign(a,palette.tolist(),backend,strength,iterations)
        if energy(candidate_labels,palette)<energy(labels,palette):labels=candidate_labels
        new=energy(labels,palette)
        history.append({'before_energy':old,'after_energy':new,'compute':stats['compute']})
    return labels,palette.tolist(),history
