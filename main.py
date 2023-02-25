import nextcord
import requests
import json
import time
from nextcord.ext import commands
from nextcord import SlashOption
from api import Rank, Normal, ARAM

# 봇 토큰
TOKEN = "DISCORD BOT TOKEN"

# Riot API 키
API_KEY = "RIOT API KEY"

intents = nextcord.Intents.all()
intents.members = True
client = commands.Bot(command_prefix='!', intents=intents)

region = 'kr'

# Function to get summoner icon URL
def get_icon(summoner_id):
    icon_url = f'https://kr.api.riotgames.com/lol/summoner/v4/summoners/{summoner_id}?api_key={API_KEY}'
    response = requests.get(icon_url)
    print(icon_url)
    # Check the response code
    if response.status_code != 200:
        print('Error:', response.status_code)
        return None
    data = json.loads(response.text)
    icon_id = data['profileIconId']
    icon_url = f'http://ddragon.leagueoflegends.com/cdn/13.3.1/img/profileicon/{icon_id}.png'
    print(icon_url)
    return icon_url

# Get rank information by summoner id
def get_rank(summoner_id):
    # Connect to database
    conn = sqlite3.connect('ranks.db')
    c = conn.cursor()

    # Create table if it doesn't exist
    c.execute('''CREATE TABLE IF NOT EXISTS ranks
                (summoner_id TEXT PRIMARY KEY, tier TEXT, rank TEXT, lp INT, win INT, loss INT)''')

    # Check if rank exists in the database
    c.execute("SELECT * FROM ranks WHERE summoner_id=?", (summoner_id,))
    row = c.fetchone()
    if row:
        return {'tier': row[1], 'rank': row[2], 'lp': row[3], 'win': row[4], 'loss': row[5]}

    # If not, get rank data from API and insert into the database
    league_url = f'https://{region}.api.riotgames.com/lol/league/v4/entries/by-summoner/{summoner_id}?api_key={API_KEY}'
    response = requests.get(league_url)

    if response.status_code != 200:
        return None

    league_data = json.loads(response.text)
    rank_data = {}
    for queue in league_data:
        if queue['queueType'] == 'RANKED_SOLO_5x5':
            rank_data['tier'] = queue['tier']
            rank_data['rank'] = queue['rank']
            rank_data['lp'] = queue['leaguePoints']
            rank_data['win'] = queue['wins']
            rank_data['loss'] = queue['losses']

    c.execute("INSERT INTO ranks (summoner_id, tier, rank, lp, win, loss) VALUES (?, ?, ?, ?, ?, ?)", (summoner_id, rank_data.get('tier'), rank_data.get('rank'), rank_data.get('lp'), rank_data.get('win'), rank_data.get('loss')))
    conn.commit()
    return rank_data if rank_data else None

def game_mode_data(mode_data):
    game_modes = {
        400: '일반',
        420: '솔로 랭크',
        430: '일반',
        440: '자유 랭크',
        450: '무작위 총력전',
        700: '격전',
        800: 'AI 대전',
        810: 'AI 대전',
        820: 'AI 대전',
        830: 'AI 대전',
        840: 'AI 대전',
        850: 'AI 대전',
        900: 'U.R.F',
        920: '포로왕',
        1020: '단일',
        1300: '돌격! 넥서스',
        1400: '궁극기 주문서',
        2000: '튜토리얼',
        2010: '튜토리얼',
        2020: '튜토리얼'
    }
    return game_modes.get(mode_data, None)

def game_map_data(map_data):
    game_maps = {
        1: '소환사의 협곡',
        2: '소환사의 협곡',
        3: '튜토리얼 맵',
        4: '뒤틀린 숲',
        8: '수정의 상처',
        10: '뒤틀린 숲',
        11: '소환사의 협곡',
        12: '칼바람 나락',
        14: '도살자의 다리',
        16: '우주 유적',
        18: '발로란 도시 공원',
        19: 'Substructure 43',
        20: 'Crash Site',
        21: 'Nexus Blitz',
        22: 'Convergence'
    }
    return game_maps.get(map_data, None)

# Function to get recent match history

def get_recent_matches(puuid, region):
    start = time.time()
    matches_url = f'https://{region}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?start=0&count=5&api_key={API_KEY}'
    response = requests.get(matches_url)
    match_ids = json.loads(response.text)
    matches = []
    match_data_dict = {}
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        future_to_match_id = {}
        for match_id in match_ids:
            match_url = f'https://{region}.api.riotgames.com/lol/match/v5/matches/{match_id}?api_key={API_KEY}'
            future = executor.submit(requests.get, match_url)
            future_to_match_id[future] = match_id
        
        for future in concurrent.futures.as_completed(future_to_match_id):
            match_id = future_to_match_id[future]
            try:
                match_data = json.loads(future.result().text)
                match_data_dict[match_id] = match_data
            except:
                match_data_dict[match_id] = None

    for match_id in match_ids:
        if match_id in match_data_dict:
            match_data = match_data_dict[match_id]
            try:
                participant = next(p for p in match_data['info']['participants'] if p['puuid'] == puuid)
                champion_name = get_champion_name(participant['championId'])
                game_mode = game_mode_data(match_data['info']['queueId'])
                match = {
                    'gamemode': game_mode,
                    'champion_name': champion_name,
                    'win': participant['win'],
                    'kda': f"{participant['kills']}/{participant['deaths']}/{participant['assists']}"
                }
                matches.append(match)
            except (KeyError, StopIteration):
                continue
    print(f'get_recent_matches_time:{time.time() - start}초')
    return matches

def get_champion_name(champion_id):
    # Connect to database
    conn = sqlite3.connect('champions.db')
    c = conn.cursor()

    # Create table if it doesn't exist
    c.execute('''CREATE TABLE IF NOT EXISTS champions
                (id INT PRIMARY KEY, name TEXT)''')

    # Check if champion exists in the database
    c.execute("SELECT name FROM champions WHERE id=?", (champion_id,))
    row = c.fetchone()
    if row:
        return row[0]

    # If not, get champion data from API and insert into the database
    champion_url = f'http://ddragon.leagueoflegends.com/cdn/13.3.1/data/ko_KR/champion.json'
    response = requests.get(champion_url)
    data = json.loads(response.text)
    champion_data = data['data']
    for champion in champion_data.values():
        if int(champion['key']) == champion_id:
            champion_name = champion['name']
            c.execute("INSERT INTO champions (id, name) VALUES (?, ?)", (champion_id, champion_name))
            conn.commit()
            return champion_name

    # If no matching champion found, return 'Unknown'
    return 'Unknown'

# Event to handle incoming messages
@client.slash_command(name='rank', description='소환사의 전적을 검색합니다.')
async def search_rank(ctx, summoner_name: str = SlashOption(description='소환사 이름을 입력해주세요.')):
    start = time.time()
    # Check if the message is a command and from an authorized user
    if ctx.user == client.user:
        return
    
    response_msg = await ctx.send(f'```css\n약 3초 정도 소요됩니다.```')  

    try:
        if len(summoner_name) == 2:
            summoner_name = summoner_name[0] + ' ' + summoner_name[1]
        else:
            summoner_name = summoner_name
    except TypeError:
         await response_msg.edit(f'```css\nsummoner_name을 선택하고 소환사 이름을 입력해주세요.```')
         return
        
    region = 'kr'
    async with aiohttp.ClientSession() as session:
        summoner_url = f'https://{region}.api.riotgames.com/lol/summoner/v4/summoners/by-name/{summoner_name}?api_key={API_KEY}'
        async with session.get(summoner_url) as response:
            if response.status != 200:
                await response_msg.edit(f'```css\n소환사를 찾을 수 없습니다.```')
                return
            data = await response.json()

    summoner__name = data['name']
    summoner_id = data['id']
    puuid = data['puuid']
    print(f"ID:{summoner_id}")

    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_rank = executor.submit(get_rank, summoner_id)
        future_icon = executor.submit(get_icon, summoner_id)
        rank_data = future_rank.result()
        icon_url = future_icon.result()
    '''
    if not rank_data:
        await message.channel.send('')
        return'''

    tier = rank_data.get('tier')
    tier_rank = rank_data.get('rank')
    print(tier)
    if tier == 'MASTER':
        tier_rank = ''
    elif tier == 'GRANDMASTER':
        tier_rank = ''
    elif tier == 'CHALLENGER':
        tier_rank = ''
    rank = tier_rank
    print(rank)
    lp = rank_data.get('lp')
    print(lp)
    win = rank_data.get('win')
    print(win)
    loss = rank_data.get('loss')
    print(loss)

    recent_matches = get_recent_matches(puuid, 'asia')
    # Create and send embed message
    re_name = summoner_name.strip().replace(' ', '%20')
    opggurl= f'https://www.op.gg/summoners/kr/{re_name}/'
    embed = nextcord.Embed(title=summoner__name, color=nextcord.Color.blue(), url=opggurl)
    embed.set_thumbnail(url=icon_url)
    
    if tier is None:
        tier = '언랭'
    if rank is None:
        rank = ''
    if lp is None:
        lp = ''
    else:
        lp = f'({lp}LP)'
    if win is None:
        winper = ''
        win = '언랭'
    else:
        winper = f'({win/(win+loss)*100:.2f}%)'
        win = f'{win}승'
    if loss is None:
        loss = ''
    else:
        loss = f'{loss}패'
    embed.add_field(name='랭크', value=f'```css\n{tier} {rank}{lp}\n```')
    embed.add_field(name='승률', value=f'```css\n{win} {loss}{winper}\n```')
    if tier == '언랭':
        embed.set_author(name=ctx.user.name)
        print('tier = 언랭')
    elif tier is not None:
        tier_url = f'https://opgg-static.akamaized.net/images/medals_new/{tier.lower()}.png?image=q_auto:best&v=1'
        embed.set_author(name= ctx.user.name, icon_url=tier_url)
        print(tier_url)


    #MMR API 멀티스레딩
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [executor.submit(Rank, summoner_name),
                executor.submit(Normal, summoner_name),
                executor.submit(ARAM, summoner_name)]
        _Rank, _Normal, _ARAM = [f.result() for f in futures]
    
    embed.add_field(name='솔로랭크', value='```css\n{}\n```'.format(_Rank[0]), inline = False)
    embed.add_field(name='노말', value='```css\n{}\n```'.format(_Normal[0]), inline = False)
    embed.add_field(name='무작위 총력전', value='```css\n{}\n```'.format(_ARAM[0]), inline = False)
    
    # Add recent match summaries
    match_summary = ' '.join([f'```css\n{"🔵" if match["win"] else "🔴"} [{match["gamemode"]}] {match["champion_name"]}: {match["kda"]}```' for match in recent_matches])
    if match_summary:
        embed.add_field(name='최근 전적', value=match_summary, inline=False)
    await ctx.channel.send(embed=embed)
    await response_msg.edit(f'```css\n검색이 완료 되었습니다.\n{time.time() - start}초```')
    print("search_rank_time :", time.time() - start)
    
# Event to handle incoming messages
@client.slash_command(name='ingame', description='소환사의 인게임 정보를 검색합니다.')
async def search_ingame(ctx, summoner_name: str  = SlashOption(description="소환사 이름을 입력해주세요.")):
    start = time.time()
    # Check if the message is a command and from an authorized user
    if ctx.user == client.user:
        return
    
    response_msg = await ctx.send(f'```css\n약 2초 정도 소요됩니다.```')
    
    try:
        if len(summoner_name) == 2:
            summoner_name = summoner_name[0] + ' ' + summoner_name[1]
        else:
            summoner_name = summoner_name
    except TypeError:
         await response_msg.edit(f'```css\nsummoner_name을 선택하고 소환사 이름을 입력해주세요.```')
         return
       
    region = "kr"  # ex) na1, euw1
    endpoint = f"https://{region}.api.riotgames.com/lol/spectator/v4/active-games/by-summoner/"
    
    # Get summoner ID from summoner name
    summoner_url = f"https://{region}.api.riotgames.com/lol/summoner/v4/summoners/by-name/{summoner_name}?api_key={API_KEY}"
    print(summoner_url)
    response = requests.get(summoner_url)
    print(response)
    if response.status_code != 200:
        await response_msg.edit(f'```css\n소환사를 찾을 수 없습니다.```')
        return
    data = response.json()
    summoner_id = data['id']
    summoner__name = data['name']
    # Get game info from summoner ID
    game_url = endpoint + summoner_id + '?api_key=' + API_KEY
    print(game_url)
    response = requests.get(game_url)
    game_data = response.json()
    # Check if the summoner is in game
    if "status" in game_data:
        await response_msg.edit(f'```css\n게임중이 아닙니다.```')
        return
    
    # Create Embed
    embed = nextcord.Embed(title="인게임 정보", color=0x00ff00)
    for smsm in game_data['participants']:
        rank_data = get_rank(smsm['summonerId'])
        print(rank_data)
    participants = [[get_champion_name(participant['championId']), participant['summonerName'], get_rank(participant['summonerId'])] for participant in game_data['participants']]
    print(participants)
    banpick_names = []
    for bannedChampion in game_data["bannedChampions"]:
        banpick_name = get_champion_name(bannedChampion['championId'])
        banpick_names.append(banpick_name)

    # Get banpick information for each team
    red_team_bans = []
    blue_team_bans = []
    for banpick_name in banpick_names:
        if len(blue_team_bans) < 5:
            blue_team_bans.append(banpick_name)
        else:
            red_team_bans.append(banpick_name)

    # Create Embed
    embed = nextcord.Embed(title="인게임 정보", color=0x00ff00)

    game_mode = game_mode_data(game_data["gameQueueConfigId"])
    game_map = game_map_data(game_data["mapId"])
    # Add game info to the Embed
    embed.add_field(name="게임모드", value=f'```css\n[{game_mode}] {game_map}```', inline=False)


    # Add players to the Embed
    blue_team_value = ''
    red_team_value = ''
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [executor.submit(get_rank, participant['summonerId']) for participant in game_data['participants']]
        for i, participant in enumerate(game_data['participants']):
            team_id = "Blue" if i < 5 else "Red"
            champion_name, summoner_name = get_champion_name(participant['championId']), participant['summonerName']
            tier = futures[i].result()
            summoner_name = summoner_name.strip()
            value = f"{champion_name} ({summoner_name})"
            tier_tier = tier['tier']
            tier_rank = tier['rank']
            if tier_tier == 'MASTER':
                tier_rank = ''
            elif tier_tier == 'GRANDMASTER':
                tier_rank = ''
            elif tier_tier == 'CHALLENGER':
                tier_rank = ''
            try:
                value2 = f"{tier['tier']} {tier_rank}({tier['lp']}LP)"
            except KeyError:
                value2 = '언랭'
            if team_id == "Red":
                red_team_value += f"{value}\n{value2}\n\n"
            else:
                blue_team_value += f"{value}\n{value2}\n\n"
    '''
    # Get observer URL
    observer_url = game_data.get("observers", {}).get("encryptionKey", "")
    '''
    
    # Send Embed
    if banpick_names:
        red_team_ban_str = '**밴픽**: ' + ', '.join(red_team_bans) if red_team_bans else ''
        blue_team_ban_str = '**밴픽**: ' + ', '.join(blue_team_bans) if blue_team_bans else ''
        embed.add_field(name='Blue team', value=f'```css\n{blue_team_value}\n{blue_team_ban_str}```', inline=True)
        embed.add_field(name='Red team', value=f'```css\n{red_team_value}\n{red_team_ban_str}```', inline=True)
    else:
        embed.add_field(name='Blue team', value=f'```css\n{blue_team_value}```', inline=True)
        embed.add_field(name='Red team', value=f'```css\n{red_team_value}```', inline=True)
        
    '''
    # Add observer URL to the Embed
    if observer_url:
        embed.add_field(name="관전 URL", value=f"spectator://kr.lol.riotgames.com:80/observer-mode/rest/encrypt/{observer_url}", inline=False)
    '''
    
    
    # Add OPGG link to the Embed
    re_name = summoner__name.strip().replace(' ', '%20')
    opgg_url = f'https://op.gg/summoners/{region}/{re_name}/ingame'
    embed.description = f'[OP.GG에서 {summoner__name}님의 게임 관전하기]({opgg_url})'
    
    await ctx.channel.send(embed=embed)
    await response_msg.edit(f'```css\n검색이 완료 되었습니다.\n{time.time() - start}초```') 
    print("search_ingame_time :", time.time() - start)
        
@client.event
async def on_ready():
    print("---------------    CONNECTED    ---------------")
    print(f"  봇 이름 : {client.user.name}")
    print(f"  봇 ID : {client.user.id}")
    print("-----------------------------------------------")

client.run(TOKEN)
