"""Generate dated profile SVGs from GitHub data without third-party stats services."""
from pathlib import Path
from datetime import datetime, timezone
from collections import Counter
import html
import json
import subprocess

USERNAME = 'kvianAR'
ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'assets'
ASSETS.mkdir(exist_ok=True)
STAMP = datetime.now(timezone.utc).strftime('%d %b %Y · UTC')

def api(endpoint, **fields):
    command = ['gh', 'api', endpoint]
    for name, value in fields.items():
        command.extend(['-f', f'{name}={value}'])
    return json.loads(subprocess.check_output(command, text=True))

pages = json.loads(subprocess.check_output(['gh', 'api', '--paginate', '--slurp', f'users/{USERNAME}/repos?per_page=100'], text=True))
repos = [repo for page in pages for repo in page if not repo['private']]
projects = [repo for repo in repos if not repo['fork'] and not repo['archived'] and repo['name'].lower() != USERNAME.lower()]
languages = Counter()
for repo in projects:
    languages.update(api(f'repos/{USERNAME}/{repo["name"]}/languages'))
query = '''query { user(login:"kvianAR") { contributionsCollection { contributionCalendar { totalContributions weeks { contributionDays { date contributionCount } } } } } }'''
calendar = api('graphql', query=query)['data']['user']['contributionsCollection']['contributionCalendar']
days = [day for week in calendar['weeks'] for day in week['contributionDays']]
active_days = sum(day['contributionCount'] > 0 for day in days)

def svg(width, height, title, content):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title"><title id="title">{html.escape(title)}</title><rect x="1" y="1" width="{width-2}" height="{height-2}" rx="18" fill="#11172b" stroke="#353657"/><g font-family="Arial,sans-serif">{content}</g></svg>'''

cards = [('Public repositories', len(repos)), ('Original public projects', len(projects)), ('Year contributions', calendar['totalContributions']), ('Active days this year', active_days)]
content = f'<text x="28" y="36" font-size="13" fill="#a8a7c4">BUILDING IN PUBLIC</text><text x="872" y="36" text-anchor="end" font-size="11" fill="#929bb5">{STAMP}</text>'
for index,(label,value) in enumerate(cards):
    x=28+index*220
    content += f'<text x="{x}" y="101" font-weight="700" font-size="40" fill="{["#77e5c4","#b7adff","#89b4ff","#f3c58d"][index]}">{value}</text><text x="{x}" y="135" font-size="12" fill="#cad1e3">{label}</text>'
(ASSETS/'github-stats.svg').write_text(svg(900,166, f'GitHub snapshot for {USERNAME}: '+', '.join(f'{value} {label}' for label,value in cards), content))

top = languages.most_common(5)
total = sum(languages.values()) or 1
palette = {'JavaScript':'#f4d35e','Python':'#89b4ff','HTML':'#ef9b76','CSS':'#b7adff','TypeScript':'#75b6ee'}
content = '<text x="28" y="37" font-size="13" fill="#a8a7c4">LANGUAGES IN MY PUBLIC PROJECTS</text>'
content += '<text x="28" y="59" font-size="11" fill="#929bb5">Source bytes across original, non-archived public project repositories</text>'
left = 28
for index,(language,count) in enumerate(top):
    width=count/total*844
    color=palette.get(language,'#77e5c4')
    content+=f'<rect x="{left:.2f}" y="82" width="{width:.2f}" height="18" fill="{color}"/>'
    x=28+index*166
    content+=f'<circle cx="{x+5}" cy="129" r="4" fill="{color}"/><text x="{x+17}" y="134" font-size="12" fill="#e7eaf4">{html.escape(language)} {count/total*100:.1f}%</text>'
    left+=width
(ASSETS/'languages.svg').write_text(svg(900,160, 'Language distribution: '+', '.join(f'{name} {count/total*100:.1f} percent' for name,count in top), content))

content = '<text x="28" y="36" font-size="13" fill="#a8a7c4">A YEAR OF GITHUB ACTIVITY</text>'
content += f'<text x="872" y="36" text-anchor="end" font-size="11" fill="#929bb5">{days[0]["date"]} → {days[-1]["date"]}</text>'
colors=['#202841','#454471','#6968a5','#9a8be0','#c1acff']
for column,week in enumerate(calendar['weeks']):
    for day in week['contributionDays']:
        row=(datetime.fromisoformat(day['date']).weekday()+1)%7
        count=day['contributionCount']
        level=0 if count==0 else 1 if count<3 else 2 if count<6 else 3 if count<10 else 4
        content+=f'<rect x="{28+column*16}" y="{57+row*16}" width="12" height="12" rx="3" fill="{colors[level]}"><title>{day["date"]}: {count} contributions</title></rect>'
content+='<text x="28" y="195" font-size="11" fill="#929bb5">Actual contribution dates and counts from GitHub · generated snapshot</text>'
for index,color in enumerate(colors): content+=f'<rect x="{774+index*18}" y="183" width="12" height="12" rx="3" fill="{color}"/>'
(ASSETS/'activity.svg').write_text(svg(900,217, 'Actual contribution calendar for '+USERNAME, content))
(ASSETS/'snapshot.json').write_text(json.dumps({'generated_at':datetime.now(timezone.utc).isoformat(),'public_repositories':len(repos),'original_public_projects':len(projects),'year_contributions':calendar['totalContributions'],'active_days':active_days,'languages_in_source_bytes':dict(languages)},indent=2)+'\n')
print(f'Generated profile cards: {len(repos)} public repositories, {len(projects)} original public projects, {calendar["totalContributions"]} year contributions.')
