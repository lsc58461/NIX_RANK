'''
API Link : https://dev.whatismymmr.com/
This code uses the api on the site above to retrieve the mmr of the League of Legends.
'''


import requests
import os
import time

import requests
token = 'WHATISMYMMR TOKEN'
URL = 'https://kr.whatismymmr.com/api/v1/summoner?name={}&apiKey={}'

def get_summoner_data(search, game_type):
    start = time.time()
    url = URL.format(search, token)
    try:
        read_json = requests.get(url).json()
        error = read_json.get('error')
        if error:
            error_code = error.get('code')
            error_msgs = {
                0: '예기치 않은 내부 서버 오류입니다.',
                1: '데이터베이스에 연결할 수 없습니다.',
                100: '소환사는 기록에 없습니다.',
                101: '소환사에 대한 최근 MMR 데이터가 없습니다.',
                200: '"이름" 쿼리 매개변수가 없습니다.',
                9001: '요청이 너무 많습니다.',
            }
            error_msg = error_msgs.get(error_code, '알 수 없는 오류가 발생했습니다.')
            return error_msg, None

        mmr_data = read_json.get(game_type, None)
        if mmr_data is None:
            return '데이터가 충분하지 않습니다.', None

        avg = mmr_data.get('avg', None)
        err = mmr_data.get('err', None)
        closest_rank = mmr_data.get('closestRank', None)
        percentile = mmr_data.get('percentile', None)
        if avg is None:
            return '데이터가 충분하지 않습니다.', None

        percentile_text = '하위' if percentile < 50 else '상위'
        result_str = f'[MMR] {avg}±{err}\n\n{closest_rank}의 {percentile_text} {percentile}%의 소환사들과 비슷합니다.'
        result_val = f'{avg}±{err}'
        print("time :", time.time() - start)
        return result_str, result_val

    except:
        return '잠시 후 다시 시도해주세요.\n문제가 계속된다면 문의 바랍니다.', None

def Rank(search='hide on bush'):
    return get_summoner_data(search, 'ranked')

def Normal(search='hide on bush'):
    return get_summoner_data(search, 'normal')

def ARAM(search='hide on bush'):
    return get_summoner_data(search, 'ARAM')