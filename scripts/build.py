#!/usr/bin/env python3
"""Build a portable, dependency-free academic site for GitHub Pages."""
from pathlib import Path
import html
import json
import posixpath
import shutil
import sys
import tempfile
import subprocess

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs'
RESEARCH = json.loads((ROOT / 'content/research.json').read_text())
EXPERIENCE = json.loads((ROOT / 'content/experience.json').read_text())
SETTINGS = json.loads((ROOT / 'content/site.json').read_text())
LIFE = json.loads((ROOT / 'content/life.json').read_text())
MEDIA = json.loads((ROOT / 'content/media.json').read_text())
PHOTO_TEXT = {p['id']: p for s in LIFE['sections'] for p in s['photos']}
COVERS = json.loads((ROOT / 'content/research-covers.json').read_text())
NAME = SETTINGS['name']
EMAIL = SETTINGS['email']
GITHUB = SETTINGS['github']
PUBLIC_URL = SETTINGS['public_url'].rstrip('/')
DESCRIPTION = 'Sean Wan studies multimodal learning, vision-language models, and reasoning at Duke University and Duke Kunshan University. Seeking Ph.D. opportunities for Fall 2027.'
PORTRAIT = '/assets/images/sean-wan-portrait.jpg'

def esc(value):
    return html.escape(str(value), quote=True)

def url(target, route):
    if not target.startswith('/'):
        return target
    path, sep, fragment = target.partition('#')
    source_dir = posixpath.dirname(route)
    relative = posixpath.relpath(path.lstrip('/') or '.', source_dir or '.')
    if path.endswith('/'):
        relative += '/'
    return relative + (sep + fragment if sep else '')

def link(label, target, route, cls=''):
    return f'<a href="{esc(url(target, route))}"' + (f' class="{cls}"' if cls else '') + f'>{esc(label)}</a>'

def diagram(project, route, linked=True):
    cover = COVERS[project['id']]
    graphic = f'<img src="{esc(url(cover["path"],route))}" width="720" height="460" alt="{esc(cover["alt"])}" loading="lazy" decoding="async">'
    if linked:
        graphic = f'<a href="{esc(url("/research/"+project["id"]+"/",route))}" aria-label="Read about {esc(project["shortTitle"])}">{graphic}</a>'
    else:
        graphic = f'<a href="{esc(url(cover["path"],route))}" data-lightbox data-caption="{esc(cover["caption"])}" aria-label="Enlarge research illustration">{graphic}</a>'
    return '<div class="research-cover">' + graphic + '</div>'

def photo_image(photo_id, route, sizes='(max-width: 760px) 90vw, 480px', eager=False):
    media, text = MEDIA[photo_id], PHOTO_TEXT[photo_id]
    srcset = ', '.join(f'{url(x["path"],route)} {x["width"]}w' for x in media.get('variants',[]))
    responsive = f' srcset="{esc(srcset)}" sizes="{esc(sizes)}"' if srcset else ''
    rotation = ' class="rotate-180"' if media.get('rotation') == 180 else ''
    return f'<img{rotation} src="{esc(url(media["src"],route))}"{responsive} width="{media["width"]}" height="{media["height"]}" alt="{esc(text["alt"])}" loading="{"eager" if eager else "lazy"}" decoding="async">'

def gallery(ids, route, group, cls=''):
    figures = []
    sizes = '(max-width: 760px) calc((100vw - 55px) / 2), 220px'
    if 'gallery-single' in cls:
        sizes = '(max-width: 360px) calc(100vw - 40px), 320px'
    elif 'orientation-gallery' in cls:
        sizes = '(max-width: 760px) 50vw, 360px'
    for photo_id in ids:
        media, text = MEDIA[photo_id], PHOTO_TEXT[photo_id]
        figures.append(f'<figure class="photo {esc(photo_id)}"><a class="photo-link" href="{esc(url(media["full"],route))}" data-lightbox data-caption="{esc(text["caption"])}" aria-label="View photo: {esc(text["caption"])}">{photo_image(photo_id,route,sizes)}<span class="photo-enlarge" aria-hidden="true">View photo ↗</span></a><figcaption>{esc(text["caption"])}</figcaption></figure>')
    return f'<div class="photo-grid {cls}" data-gallery="{esc(group)}">'+''.join(figures)+'</div>'

def photo_dialog():
    return '''<dialog id="photo-dialog" aria-label="Photo viewer"><div class="lightbox-toolbar"><p id="lightbox-counter" aria-live="polite"></p><button class="lightbox-close" type="button" aria-label="Close photo viewer">Close ×</button></div><div class="lightbox-stage"><button class="lightbox-prev" type="button" aria-label="Previous photo">←</button><figure><img id="lightbox-image" alt=""><figcaption id="lightbox-caption"></figcaption></figure><button class="lightbox-next" type="button" aria-label="Next photo">→</button></div><p class="lightbox-message" role="status"></p></dialog>'''

def resources(project, route, details=True):
    items = []
    if details:
        items.append(link('Project overview ↗', f"/research/{project['id']}/", route))
    items += [link(item['label'] + ' ↗', item['url'], route) for item in project['links']]
    return '<div class="resource-links">' + ''.join(items) + '</div>'

def research_row(p, route):
    category = 'Multimodal AI' if p['id'] in ('statedelta', 'virel-budget') else 'Agent evaluation' if p['id'] == 'stableeval' else 'Algorithm selection'
    status = 'In preparation' if p['status'] == 'Manuscript in preparation' else 'Workshop paper'
    subtitle = p['theme']
    level = 2 if route == 'research/index.html' else 3
    return f'''<article class="research-row" id="{p['id']}" data-category="{category}">
      {diagram(p, route)}<div><div class="eyebrow">{esc(subtitle)}</div>
      <h{level} class="research-title">{link(p['shortTitle'], '/research/'+p['id']+'/', route)}</h{level}>
      <div class="meta"><span class="status">{status}</span> {esc(p['venue'])}</div>
      <p>{esc(p['summary'])}</p>{resources(p,route)}</div></article>'''

def news_rows(route, count=None):
    items = EXPERIENCE['news'][:count]
    return ''.join(f'<article class="news-row"><time>{esc(n["date"])}</time><div><strong>{link(n["title"],n["href"],route)}</strong><p>{esc(n["summary"])}</p></div></article>' for n in items)

def awards_rows(items):
    return '<ul class="honor-list">' + ''.join(f'<li>{esc(a["name"])}<span>{esc(a["date"])}</span></li>' for a in items) + '</ul>'

def heading(title, subtitle='', eyebrow=''):
    return '<div class="page-top">' + (f'<p class="eyebrow">{esc(eyebrow)}</p>' if eyebrow else '') + f'<h1>{esc(title)}</h1>' + (f'<p class="lede">{esc(subtitle)}</p>' if subtitle else '') + '</div>'

def filters(target, categories):
    return f'<div class="filter-bar" data-filter-group="{target}" role="group" aria-label="Filter entries">' + ''.join(f'<button class="filter" type="button" data-filter="{esc(c)}" aria-pressed="{str(i==0).lower()}">{esc("All" if c=="all" else c)}</button>' for i,c in enumerate(['all']+categories)) + f'</div><p id="{target}-status" class="sr-only" role="status" aria-live="polite"></p>'

def entry(item, route):
    organization = link(item['organization'],item['url'],route) if item['url'] else esc(item['organization'])
    photos = {'student-leaders-board':(['student-leader-award'],'gallery-single'), 'orientation':(['orientation-2024','orientation-2025','orientation-2026'],'orientation-gallery'), 'peer':(['peer-yuanling'],'gallery-single')}
    media = gallery(*[photos[item['id']][0],route,item['id'],photos[item['id']][1]+' community-media']) if route.startswith('community/') and item['id'] in photos else ''
    return f'''<article class="entry" id="{esc(item['id'])}"><div class="entry-date">{esc(item['dates'])}<span class="place">{esc(item['location'])}</span></div><div><h3>{organization}</h3><p class="role">{esc(item['role'])}</p><p class="summary">{esc(item['summary'])}</p><ul>''' + ''.join(f'<li>{esc(c)}</li>' for c in item['contributions']) + '</ul>'+media+'</div></article>'

def layout(route, title, content, active='Home', description=DESCRIPTION):
    canonical = PUBLIC_URL + '/' + route.removesuffix('index.html')
    nav = ''
    for label,target in [('Home','/'),('Research','/research/'),('Experience','/experience/'),('Community','/community/'),('Life','/life/'),('CV','/cv/')]:
        current = ' aria-current="page"' if label == active else ''
        cls = ' class="cv-link"' if label == 'CV' else ''
        nav += f'<a href="{esc(url(target,route))}"{current}{cls}>{label}</a>'
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title><meta name="description" content="{esc(description)}">
<meta name="theme-color" content="#fffcfb"><meta property="og:type" content="website"><meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(description)}"><meta property="og:image" content="{esc(PUBLIC_URL+PORTRAIT)}"><meta property="og:url" content="{esc(canonical)}"><link rel="canonical" href="{esc(canonical)}">
<link rel="icon" type="image/svg+xml" href="{url('/assets/favicon.svg',route)}"><link rel="stylesheet" href="{url('/assets/style.css',route)}"><script src="{url('/assets/site.js',route)}" defer></script>
<noscript><style>.filter-bar{{display:none}}@media(max-width:760px){{.nav{{display:flex;position:static;padding:0;gap:8px 15px}}.nav-inner{{flex-wrap:wrap;padding-top:16px;padding-bottom:16px}}.menu-toggle{{display:none}}}}</style></noscript>
</head><body><a class="skip" href="#main">Skip to content</a>
<header class="site-header"><div class="container nav-inner"><a class="brand" href="{url('/',route)}" aria-label="Weilin Sean Wan home"><span>Weilin Sean Wan</span></a><button class="menu-toggle" type="button" aria-expanded="false" aria-controls="main-navigation">Menu</button><nav class="nav" id="main-navigation" aria-label="Main navigation">{nav}</nav></div></header>
<main id="main" class="container">{content}</main>
<footer class="site-footer"><div class="container footer-inner"><div>© 2026 Weilin Sean Wan <span aria-hidden="true">·</span> Updated November 2026</div><div class="footer-links">{link('News','/news/',route)}{link('Timeline','/timeline/',route)}{link('GitHub',GITHUB,route)}{link('Email','mailto:'+EMAIL,route)}</div></div></footer>{photo_dialog()}</body></html>'''

def home():
    r = 'index.html'
    research = ''.join(research_row(p,r) for p in RESEARCH[:3])
    education = ''.join(f'<article class="education-item"><h3>{esc(e["institution"])}</h3><p>{esc(e["degree"])}</p><p class="muted">Expected May 2027</p></article>' for e in EXPERIENCE['education'])
    selected_awards = [EXPERIENCE['awards'][i] for i in [0,2,6]]
    return f'''<section class="hero" aria-labelledby="intro-name"><div class="hero-photo"><div class="portrait-frame"><img class="portrait" src="{url(PORTRAIT,r)}" width="800" height="1200" alt="Sean Wan wearing a blue suit in a stone archway" fetchpriority="high"></div><div class="portrait-caption"><strong>Duke University<br>Duke Kunshan University</strong><br>Dual-degree undergraduate<br>Expected graduation · May 2027</div></div>
<div><p class="eyebrow">Multimodal learning · Vision-language models</p><h1 id="intro-name">Weilin Sean Wan</h1><p class="intro">Hi, I’m Sean Wan, an undergraduate in the <a href="https://www.duke.edu/">Duke University</a>–<a href="https://www.dukekunshan.edu.cn/">Duke Kunshan University</a> dual-degree program.</p><p class="intro">My research focuses on <strong>multimodal learning and reasoning</strong>, particularly grounding vision-language models in visual evidence and making their inference more reliable and efficient.</p><p class="intro">I work with Kaizhu Huang on grounded procedural generation, Luyao Zhang and Dongping Liu on reliable AI evaluation, and Mustafa Mısır on cost-aware algorithm selection.</p><div class="application">I am seeking <strong>Ph.D. opportunities for Fall 2027</strong> in multimodal AI, vision-language models, and reasoning.</div><div class="contact-links">{link('Academic CV ↗','/assets/files/Sean-Wan-CV.pdf',r,'primary')}{link('GitHub ↗',GITHUB,r)}{link('Email ↗','mailto:'+EMAIL,r)}</div></div></section>
<section class="section" aria-labelledby="selected-research"><div class="section-head"><h2 id="selected-research">Selected research</h2>{link('All five projects →','/research/',r)}</div><p class="section-intro">Grounded reasoning, reliable inference, and careful evaluation of AI systems.</p>{research}</section>
<section class="section"><div class="section-split"><div><div class="section-head"><h2>Recent news</h2>{link('All news →','/news/',r)}</div>{news_rows(r,3)}</div><div id="education"><p class="eyebrow">Academic background</p><h2>Across Duke & DKU</h2>{education}<p class="small muted">Duke exchange semester · August–December 2025<br>Cumulative GPA · 3.810 / 4.000</p></div></div></section>
<section class="section" id="awards"><div class="section-head"><h2>Selected recognition</h2>{link('Full honors list →','/cv/#honors',r)}</div><div class="recognition-layout">{gallery(["student-leader-award"],r,"home-award","gallery-single")}{awards_rows(selected_awards)}</div></section>
<section class="section beyond"><div class="section-head"><h2>Beyond research</h2>{link('More about my life →','/life/',r)}</div><div class="home-personal-copy"><p>Running with the DKU team, keeping flight logs, and spending time with Dewi. A few parts of life outside my research.</p></div><div class="home-life-grid">{''.join(f'<a class="home-life-item {key}" href="{url("/life/#"+key,r)}">{photo_image(photo,r,"(max-width: 760px) calc((100vw - 68px) / 3), 280px")}<span>{label}<br><small>{caption}</small></span></a>' for key,photo,label,caption in [('running','running-race','On the run','DKU Varsity Running'),('aviation','aviation-a350','Aviation','Cockpit visits & flight logs'),('dewi','dewi-walk','Dewi','My Shiba Inu')])}</div><p class="community-footer-note">{link('Leadership, teaching & service →','/community/',r)} &nbsp; · &nbsp; {link('Explore my timeline →','/timeline/',r)}</p></section>'''

def research_index():
    r='research/index.html'
    return heading('Research','I study grounded multimodal reasoning and reliable, efficient AI. My work also explores agent evaluation and algorithm selection under limited budgets and distribution shift.','Questions, methods & evidence') + filters('research-list',['Multimodal AI','Agent evaluation','Algorithm selection']) + '<div id="research-list">' + ''.join(research_row(p,r) for p in RESEARCH) + '</div>'

def research_detail(p):
    r=f'research/{p["id"]}/index.html'
    def bullets(items):
        return '<ul>'+''.join(f'<li>{esc(x)}</li>' for x in items)+'</ul>'
    facts = [('Dates',p['dates']),('Advisor' if len(p['advisors'])==1 else 'Advisors',', '.join(p['advisors'])),('Status',p['status']),('Venue / submission plan',p['venue'])]
    findings = '<section class="article-section"><h2>Findings</h2>'+bullets(p['findings'])+'</section>' if p['findings'] else ''
    return '<article class="research-detail"><div class="page-top">'+link('← All research','/research/',r,'back-link')+f'<p class="eyebrow">{esc(p["theme"])}</p><h1>{esc(p["title"])}</h1><p class="lede">{esc(p["summary"])}</p></div><dl class="project-facts">'+''.join(f'<div><dt>{label}</dt><dd>{esc(value)}</dd></div>' for label,value in facts)+'</dl>'+resources(p,r,False)+f'<figure class="detail-figure">{diagram(p,r,False)}<figcaption>{esc(COVERS[p["id"]]["caption"])}</figcaption></figure><section class="article-section"><h2>Research question</h2><p>{esc(p["question"])}</p></section><section class="article-section"><h2>My contributions</h2>'+bullets(p['contributions'])+'</section>'+findings+'<section class="article-section"><h2>Scope & current status</h2>'+bullets(p['limitations'])+f'</section><section class="article-section"><h2>Authors & manuscript</h2><p>{esc(", ".join(p["authors"]))}</p><p class="citation">{esc(p["citation"])}</p></section></article>'

def experience():
    r='experience/index.html'
    return heading('Experience','Machine learning engineering, platform telemetry, and product work across academic publishing, collaboration tools, and sustainability.','Building & applying') + '<div class="jump-links">'+link('Industry & internships','#industry',r)+link('Product & applied projects','#projects',r)+'</div><section id="industry"><h2>Industry & internships</h2>'+''.join(entry(x,r) for x in EXPERIENCE['industry'])+'</section><section class="section" id="projects"><h2>Product & applied projects</h2>'+''.join(entry(x,r) for x in EXPERIENCE['projects'])+'</section>'

def community():
    r='community/index.html'
    teaching=''.join(f'<div class="teaching-row"><span class="teaching-role">{esc(t["role"])}</span><span>{esc(t["course"])}</span><span class="term">{esc(t["term"])}</span></div>' for t in EXPERIENCE['teaching'])
    return heading('Leadership, teaching & service','Student advocacy, peer learning, and community work at Duke and Duke Kunshan University.','Community') + '<div class="jump-links">'+link('Leadership & service','#leadership',r)+link('Teaching & mentoring','#teaching',r)+'</div><section id="leadership">'+''.join(entry(x,r) for x in EXPERIENCE['community'])+'</section><section class="section" id="teaching"><h2>Teaching & mentoring</h2><p class="section-intro">Teaching assistant and peer-tutor appointments at Duke Kunshan University.</p><div class="teaching-list">'+teaching+'</div></section>'

def life():
    r='life/index.html'
    sections = LIFE['sections'][:4]
    body = heading('Life beyond research',LIFE['intro'],'Running, aviation & everyday moments')
    body += '<nav class="life-index" aria-label="On this page">'+''.join(link(x['title'],'#'+x['id'],r) for x in sections)+link('Campus & community','/community/',r)+'</nav>'
    styles = {'running':'running-gallery','aviation':'aviation-gallery','sports':'gallery-single sports-gallery','dewi':'dewi-gallery'}
    for section in sections:
        facts = '<dl class="running-records">'+''.join(f'<div><dt>{esc(x["label"])}</dt><dd>{esc(x["value"])}</dd></div>' for x in section.get('facts',[]))+'</dl>' if section.get('facts') else ''
        body += f'<section class="life-section" id="{section["id"]}"><div class="life-section-top"><h2>{esc(section["title"])}</h2><div><p>{esc(section["body"])}</p>{facts}</div></div>'+gallery([p['id'] for p in section['photos']],r,section['id'],styles[section['id']])+'</section>'
    body += '<section class="section"><div class="section-head"><h2>Across Duke & DKU</h2></div><p class="readable">I have also been an Orientation Leader across three years of Duke and DKU programs, worked with middle-school students in Yuanling County, Hunan, and served in student leadership.</p><p>'+link('Orientation, education & student leadership →','/community/',r)+'</p><h3>Languages</h3><div class="languages"><span>Mandarin · Native</span><span>English · Fluent</span><span>Spanish · Intermediate</span><span>Cantonese · Intermediate</span></div></section>'
    return body

def cv():
    r='cv/index.html'
    edu=''.join(f'<article class="education-item"><h3>{esc(e["institution"])}</h3><p>{esc(e["degree"])}</p><p class="muted">{esc(e["dates"])}</p>'+''.join(f'<p class="small muted">{esc(d)}</p>' for d in e['details'])+'</article>' for e in EXPERIENCE['education'])
    return heading('Curriculum vitae','Education, research, teaching, and recognition.','Weilin Sean Wan')+f'''<section class="cv-panel"><div><h2>Academic CV</h2><p>My two-page academic CV includes publications and manuscripts, research experience, teaching, and service.</p><div class="contact-links">{link('Open CV PDF ↗','/assets/files/Sean-Wan-CV.pdf',r,'primary')}</div><p class="small" style="margin-top:22px">Published as Sean Wan.<br>Contact: {link(EMAIL,'mailto:'+EMAIL,r)}</p></div><div class="cv-preview"><h3>Weilin Sean Wan</h3><p>Multimodal AI · Vision-language models · Reasoning</p><div class="rule">Duke University & Duke Kunshan University<br>Expected graduation · May 2027</div><div class="rule" style="margin-top:18px">{link('Research & publications →','/research/',r)}<br>{link('Professional experience →','/experience/',r)}<br>{link('Teaching & service →','/community/',r)}</div></div></section><section class="section" id="education"><h2>Education</h2>{edu}</section><section class="section" id="honors"><h2>Honors & awards</h2>{awards_rows(EXPERIENCE['awards'])}</section><section class="section"><h2>Technical background</h2><p class="readable">Python, Java, C, scikit-learn, Jupyter, GitHub, and LaTeX. Research experience in VLM training and evaluation, multimodal learning, agentic AI workflows, and reinforcement learning.</p></section>'''

def news():
    return heading('News','Updates from research, teaching, and campus life.','Milestones')+'<div class="readable">'+news_rows('news/index.html')+'</div>'

def timeline():
    r='timeline/index.html'
    categories=list(dict.fromkeys(x['category'] for x in EXPERIENCE['timeline']))
    events=''.join(f'<article class="timeline-event" data-category="{esc(x["category"])}"><time>{esc(x["date"])}</time><div><span class="category">{esc(x["category"])}</span><h3>{link(x["title"],x["href"],r)}</h3><p>{esc(x["summary"])}</p></div></article>' for x in sorted(EXPERIENCE['timeline'],key=lambda x:x['sort'],reverse=True))
    return heading('A timeline','Education, research, product work, and community milestones, from 2023 onward.','Along the way')+filters('timeline-list',categories)+'<div class="timeline" id="timeline-list">'+events+'</div>'

def main():
    pages = {
        'index.html':(NAME,home(),'Home'),
        'research/index.html':('Research · '+NAME,research_index(),'Research'),
        'experience/index.html':('Experience · '+NAME,experience(),'Experience'),
        'community/index.html':('Community · '+NAME,community(),'Community'),
        'life/index.html':('Life · '+NAME,life(),'Life'),
        'cv/index.html':('CV · '+NAME,cv(),'CV'),
        'news/index.html':('News · '+NAME,news(),''),
        'timeline/index.html':('Timeline · '+NAME,timeline(),''),
    }
    for p in RESEARCH:
        pages[f'research/{p["id"]}/index.html']=(p['shortTitle']+' · '+NAME,research_detail(p),'Research')
    # Validate a clean build before replacing the current preview. Failed builds
    # leave the last working output intact, and clean copies remove stale assets.
    with tempfile.TemporaryDirectory(prefix='.site-build-',dir=ROOT) as staging:
        staged = Path(staging)/'docs'
        staged.mkdir()
        shutil.copytree(ROOT/'assets',staged/'assets')
        for route,(title,body,active) in pages.items():
            dest=staged/route
            dest.parent.mkdir(parents=True,exist_ok=True)
            dest.write_text(layout(route,title,body,active),encoding='utf-8')
        (staged/'.nojekyll').write_text('')
        subprocess.run([sys.executable,str(ROOT/'scripts/validate.py'),str(staged)],check=True)
        previous = Path(staging)/'previous-docs'
        if OUT.exists():
            OUT.rename(previous)
        try:
            staged.rename(OUT)
        except OSError:
            if previous.exists():
                previous.rename(OUT)
            raise
    print(f'Built {len(pages)} pages into {OUT}')

if __name__ == '__main__':
    main()
