"""Decode the processed 16-bit PNG heightmaps into TerrainDataJSON."""
from __future__ import annotations
import argparse, json, struct, zlib
from pathlib import Path

PROVENANCE = {
    "mars_jezero_local": ("MOLA MEGDR", "MGS-M-MOLA-5-MEGDR-L3-V1.0", "2.0", "https://pds-geosciences.wustl.edu/mgs/mgs-m-mola-5-megdr-l3-v1/mgsl_300x/meg128/megt44n000hb.img", "Mars", "GMM3 (mgm1025) degree/order 50 areoid"),
    "earth_salda_local": ("Copernicus DEM", "Copernicus_DSM_COG_10_N37_00_E029_00_DEM", "GLO-30 Public 2021", "https://copernicus-dem-30m.s3.amazonaws.com/Copernicus_DSM_COG_10_N37_00_E029_00_DEM/Copernicus_DSM_COG_10_N37_00_E029_00_DEM.tif", "Earth", "EGM2008 orthometric height"),
    "earth_kula_local": ("Copernicus DEM", "Copernicus_DSM_COG_10_N38_00_E028_00_DEM", "GLO-30 Public 2021", "https://dataspace.copernicus.eu/explore-data/data-collections/copernicus-contributing-missions/collections-description/COP-DEM", "Earth", "EGM2008 orthometric height"),
    "moon_shackleton_local": ("LOLA GDRDEM", "LDEM_75S_240M", "V2.0 (2017)", "https://pds-geosciences.wustl.edu/lro/lro-l-lola-3-rdr-v1/lrolol_1xxx/data/lola_gdr/polar/img/ldem_75s_240m.img", "Moon", "Height above 1737400 m sphere; not an equipotential surface"),
}
LABELS = {"earth_salda_local": "Lake Salda", "earth_kula_local": "Kula", "mars_jezero_local": "Jezero", "moon_shackleton_local": "Shackleton"}

def png16(path: Path):
    b = path.read_bytes(); assert b[:8] == b'\x89PNG\r\n\x1a\n'; pos=8; raw=b''
    while pos < len(b):
        n=struct.unpack('>I',b[pos:pos+4])[0]; typ=b[pos+4:pos+8]; dat=b[pos+8:pos+8+n]; pos += 12+n
        if typ == b'IHDR': w,h,depth,color,_,_,_=struct.unpack('>IIBBBBB',dat); assert (depth,color)==(16,0)
        elif typ == b'IDAT': raw += dat
        elif typ == b'IEND': break
    rows=[]; stride=w*2; data=zlib.decompress(raw); prev=bytearray(stride); p=0
    for _ in range(h):
        f=data[p]; p+=1; cur=bytearray(data[p:p+stride]); p+=stride
        for i in range(stride):
            a=cur[i-2] if i>=2 else 0; bb=prev[i]; c=prev[i-2] if i>=2 else 0
            if f==1: cur[i]=(cur[i]+a)&255
            elif f==2: cur[i]=(cur[i]+bb)&255
            elif f==3: cur[i]=(cur[i]+((a+bb)//2))&255
            elif f==4:
                q=a+bb-c; pa=abs(q-a); pb=abs(q-bb); pc=abs(q-c); cur[i]=(cur[i]+(a if pa<=pb and pa<=pc else bb if pb<=pc else c))&255
        rows.append([cur[i]*256+cur[i+1] for i in range(0,stride,2)]); prev=cur
    return w,h,[v for row in rows for v in row]

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('input'); ap.add_argument('metadata'); ap.add_argument('output'); ns=ap.parse_args()
    stem=Path(ns.input).stem; meta=json.loads(Path(ns.metadata).read_text()); dataset,pid,version,url,body,datum=PROVENANCE[stem]; w,h,pixels=png16(Path(ns.input)); valid=[p != int(meta['NoData']) for p in pixels]; heights=[None if not ok else p*meta['scale']+meta['offset'] for p,ok in zip(pixels,valid)]
    data={"id":stem,"name":LABELS[stem],"body":body,"width":w,"height":h,"heights":heights,"cellSizeMeters":{"x":meta['pixel_size_x_m'],"y":meta['pixel_size_y_m']},"source":dataset,"resolutionMeters":meta['pixel_size_x_m'],"dataType":"real","validMask":valid,"horizontalWindowMeters":{"width":(w-1)*meta['pixel_size_x_m'],"height":(h-1)*meta['pixel_size_y_m']},"verticalDatum":datum,"coordinateReferenceSystem":meta['crs'],"processingMetadata":{"provenance":{"dataset":dataset,"productId":pid,"version":version,"url":url},"steps":["Decoded 16-bit PNG using documented scale and offset","Preserved row-major ordering and NoData mask","Preserved processed DEM spacing"],"software":"AstroMatch processed DEM heightmap decoder"}}
    Path(ns.output).write_text(json.dumps(data,indent=2)+"\n")
if __name__=='__main__': main()
