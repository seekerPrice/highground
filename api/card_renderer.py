"""Pillow/RAQM rendering with grapheme wrapping and real TTF glyph coverage."""
from functools import lru_cache
from io import BytesIO
from pathlib import Path
import unicodedata
import regex
from fontTools.ttLib import TTFont
from PIL import Image,ImageDraw,ImageFont,features
from api.offline_card import CardContext,CardText,card_time
from api.i18n import text

ROOT=Path(__file__).with_name('fonts')
FAMILIES=('notosans','notosanssc','notosanstamil','notosansbengali','notosansdevanagari','notosansmyanmar')
PRIMARY={'zh':'notosanssc','ta':'notosanstamil','bn':'notosansbengali','ne':'notosansdevanagari','my':'notosansmyanmar'}
INK='#17324d';TEAL='#117c83';MUTED='#455f74';PAPER='#f3f8fb'

@lru_cache(maxsize=6)
def coverage(family):
    with TTFont(ROOT/(family+'.ttf'),lazy=True) as font:return frozenset(code for code,glyph in font.getBestCmap().items() if glyph!='.notdef')

@lru_cache(maxsize=120)
def font(family,size):
    if not features.check('raqm'):raise ValueError('Offline cards require Pillow RAQM shaping; rebuild the pinned Pillow with raqm=enable')
    result=ImageFont.truetype(str(ROOT/(family+'.ttf')),size,layout_engine=ImageFont.Layout.RAQM)
    axes=result.get_variation_axes()
    result.set_variation_by_axes([400 if axis['name']==b'Weight' else axis['default'] for axis in axes])
    return result


def runs(value,language,size):
    chunks=[]
    for cluster in regex.findall(r'\X',value):
        points={ord(char) for char in cluster if unicodedata.category(char)!='Cf'}
        family=next((name for name in (PRIMARY.get(language,'notosans'),*FAMILIES) if points<=coverage(name)),None)
        if family is None:raise ValueError('Card text contains a glyph unsupported by the licensed font set')
        if chunks and chunks[-1][0]==family:chunks[-1]=(family,chunks[-1][1]+cluster)
        else:chunks.append((family,cluster))
    return [(font(family,size),value) for family,value in chunks]


def width(value,language,size):return sum(face.getlength(part) for face,part in runs(value,language,size))


def wrap(value,language,size,limit=952):
    lines=[];line=''
    for cluster in regex.findall(r'\X',value):
        if cluster=='\n':lines.append(line);line='';continue
        candidate=line+cluster
        if width(candidate,language,size)>limit and line:
            split=line.rfind(' ')
            if split>0:lines.append(line[:split]);line=line[split+1:]+cluster
            else:lines.append(line);line=cluster
        else:line=candidate
    if line:lines.append(line)
    if any(width(line,language,size)>limit for line in lines):raise ValueError('Card grapheme exceeds layout width')
    return lines


def line_metrics(value,language,size):
    boxes=[face.getbbox(part,anchor='ls') for face,part in runs(value,language,size)]
    top=min((box[1] for box in boxes),default=-size)
    bottom=max((box[3] for box in boxes),default=0)
    return top,max(size,bottom-top)+8


def draw_lines(draw,lines,language,size,x,y,color):
    for line in lines:
        top,height=line_metrics(line,language,size);left=x
        for face,part in runs(line,language,size):
            draw.text((left,y-top),part,font=face,fill=color,anchor='ls');left+=face.getlength(part)
        y+=height
    return y


def render_offline_card(context:CardContext,words:CardText)->bytes:
    if not features.check('raqm'):raise ValueError('Offline cards require Pillow RAQM shaping; rebuild the pinned Pillow with raqm=enable')
    language=context.language
    points=[(context.lat,context.lng,'card_shop_pin',INK)]
    for point,key in ((context.parking,'card_parking_pin'),(context.shelter,'card_shelter_pin')):
        if point:points.append((point.lat,point.lng,key,TEAL))
    legend=' · '.join(f'{index+1}: '+text(language,point[2]) for index,point in enumerate(points))
    map_lines=wrap(legend,language,24)+wrap(text(language,'card_map_label'),language,24)
    map_height=248+sum(line_metrics(line,language,24)[1] for line in map_lines)+16
    header=([text(language,'card_simulation')] if context.is_demo else [])+[words.title,context.shop_name]
    sections=[(text(language,'card_lift_heading'),'\n'.join(words.lift_lines)),(text(language,'card_parking_heading'),words.parking_line),(text(language,'card_shelter_heading'),words.shelter_line)]
    footer=words.emergency_line+'\n'+text(language,'card_timestamp',time=card_time(context))+'\n'+words.footer
    selected=None
    for size in range(42,23,-2):
        blocks=[wrap('\n'.join(header),language,size+8),*[wrap(title+'\n'+body,language,size) for title,body in sections],wrap(footer,language,size)]
        heights=[]
        for index,lines in enumerate(blocks):
            actual=size+8 if index==0 else size
            heights.append(sum(line_metrics(line,language,actual)[1] for line in lines))
        if sum(heights)+4*24+map_height<=1792:selected=(size,blocks);break
    if selected is None:raise ValueError('Card facts exceed bounded readable layout; no clipped card is generated')
    size,blocks=selected;image=Image.new('RGB',(1080,1920),PAPER);draw=ImageDraw.Draw(image);y=64
    for index,lines in enumerate(blocks[:-1]):
        y=draw_lines(draw,lines,language,size+8 if index==0 else size,64,y,TEAL if index==0 else INK)+24
    # Source-permitted schematic: approximate relative pins, no road/depth/opening claims.
    map_top=y;draw.rounded_rectangle((64,y,1016,y+240),radius=12,fill='#e0edf2',outline='#9ebbc9',width=2)
    low_lat=min(p[0] for p in points);high_lat=max(p[0] for p in points);low_lng=min(p[1] for p in points);high_lng=max(p[1] for p in points)
    for index,(lat,lng,key,color) in enumerate(points):
        x=130+(lng-low_lng)/(high_lng-low_lng or 1)*750 if len(points)>1 else 540
        py=y+65+(high_lat-lat)/(high_lat-low_lat or 1)*90
        coincident=[i for i,point in enumerate(points) if point[:2]==(lat,lng)]
        if len(coincident)>1:
            offset=(coincident.index(index)-(len(coincident)-1)/2)*42
            draw.line((x,py,x+offset,py+25),fill=color,width=2);x+=offset;py+=25
        draw.ellipse((x-15,py-15,x+15,py+15),fill=color)
        # Numbered pins bind a localized legend without clipped long place names.
        face=font('notosans',24);draw.text((x,py),str(index+1),font=face,anchor='mm',fill='white')
    y=map_top+248
    legend=' · '.join(f'{index+1}: '+text(language,point[2]) for index,point in enumerate(points))
    y=draw_lines(draw,wrap(legend,language,24),language,24,64,y,INK)
    y=draw_lines(draw,wrap(text(language,'card_map_label'),language,24),language,24,64,y,MUTED)+16
    y=draw_lines(draw,blocks[-1],language,size,64,y,INK)
    if y>1856:raise ValueError('Card layout height exceeded; no clipped image is generated')
    stream=BytesIO();image.save(stream,format='PNG',optimize=True)
    result=stream.getvalue()
    if len(result)>10_000_000:raise ValueError('Derived card exceeds Telegram photo limit')
    return result
