from datetime import datetime

def Time():
    now = datetime.now()
    kst_now = now.strftime('%Y년 %m월 %d일 %H시 %M분 %S초)  ')
    return kst_now

    
    


    

