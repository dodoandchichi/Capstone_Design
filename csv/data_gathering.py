from datetime import datetime, timedelta
import sys
import time
import gc
import glob
import os
import subprocess
from multiprocessing import Process
from labjack import ljm

## 한 번에 전송할 수 있는 최대 데이터 요청 횟수
MAX_REQUESTS = 1728000

## T7 장치를 엽니다. "USB"는 연결 유형을 나타내며, "ANY"는 어떤 연결이든 허용한다는 것을 의미
handle = ljm.openS("T7", "ANY", "ANY")  # T7 device, Any connection, Any identifier

## 열린 장치의 정보를 가져옴
info = ljm.getHandleInfo(handle)

## info[0]: 장치의 유형을 가져옴
deviceType = info[0]

## 스캔할 아날로그 입력 채널의 이름을 리스트로 지정
aScanListNames = ["AIN0", "AIN1", "AIN2", "AIN13"]

## 스캔할 아날로그 입력 채널의 수를 계산
numAddresses = len(aScanListNames)

## 스캔할 아날로그 입력 채널의 주소를 계산
aScanList = ljm.namesToAddresses(numAddresses, aScanListNames)[0]

## 스캔 속도를 설정, 이 값은 초당 스캔할 횟수
scanRate = 1500

## 한 번에 읽어들일 스캔 횟수를 설정
scansPerRead = int(scanRate / 2)

try:
    if deviceType == ljm.constants.dtT4:
        aNames = ["AIN0_RANGE", "AIN1_RANGE", "STREAM_SETTLING_US", "STREAM_RESOLUTION_INDEX"]
        aValues = [10.0, 10.0, 0, 0]
    else:
        ljm.eWriteName(handle, "STREAM_TRIGGER_INDEX", 0)
        ljm.eWriteName(handle, "STREAM_CLOCK_SOURCE", 0)
        aNames = ["AIN_ALL_NEGATIVE_CH", "AIN0_RANGE", "AIN1_RANGE", "AIN2_RANGE", "AIN13_RANGE", "STREAM_SETTLING_US", "STREAM_RESOLUTION_INDEX"]
        aValues = [ljm.constants.GND, 10.0, 10.0, 10.0, 10.0, 0, 0]

    # Write the analog inputs' negative channels, ranges, stream settling time
    # and stream resolution configuration.
    numFrames = len(aNames)
    ljm.eWriteNames(handle, numFrames, aNames, aValues)

    # Configure and start stream
    scanRate = ljm.eStreamStart(handle, scansPerRead, numAddresses, aScanList, scanRate)
    print("\nStream started with a scan rate of %0.0f Hz." % scanRate)
    print("\nPerforming %i stream reads." % MAX_REQUESTS)
    start = datetime.now()
    print(start)
    totScans = 0
    totSkip = 0     # Total skipped samples



    i = 1
    while i <= MAX_REQUESTS:
        try:
            ## 현재 시간 출력
            gc.collect()
            time_number = time.time()
            time_number_UTC = time_number - 32400
            ss = datetime.fromtimestamp(time_number)

            f = open('E:/csv/stream%s_%s_%s_%s_%s.csv' %(ss.year, ss.month, ss.day, ss.hour, ss.minute), 'a+')
            #f = open('C:/Users/kongs/OneDrive/바탕 화면/csv/stream_test.csv', 'a+')
            #print (f.tell())
            ret = ljm.eStreamRead(handle)

            data = ret[0][0:(scansPerRead * numAddresses)]
            scans = len(data) / numAddresses
            totScans += scans
            curSkip = data.count(-9999.0)
            totSkip += curSkip

            if f.tell() == 0 :
                readStr = "motor1_x,motor1_y,motor1_z,sound,time"+"\n"
            else:
                readStr = ""
            timer = 0

            for j in range(0, scansPerRead):
                for k in range(0, numAddresses):
                    readStr += "%f," % (data[j * numAddresses + k])
                timer += (1/scanRate)
                readStr += "%s" % (datetime.fromtimestamp(time_number_UTC + timer).isoformat("T") + "Z")
                readStr += "\n"

            print(readStr, file=f, end="")
            i += 1
        
        ## stream interrupt가 발생하면 예외처리하는 구문
        except KeyboardInterrupt:
            # Stop the data stream and close the device
            ljm.eStreamStop(handle)
            ljm.close(handle)
            break        

    ## end
    end = datetime.now()
    tt = (end - start).seconds + float((end - start).microseconds) / 1000000
    print("Timed Sample Rate = %f samples/second" % (totScans * numAddresses/tt))



except ljm.LJMError as e:
    # Handle LJM errors here
    print("LJM Error:", e)
except Exception as e:
    # Handle other exceptions here
    print("Error:", e)
finally:
    # Stop the data stream and close the device
    ljm.eStreamStop(handle)
    ljm.close(handle)


try:
    print("\nStop Stream")
    ljm.eStreamStop(handle)
except ljm.LJMError:
    ljme = sys.exc_info()[1]
    print(ljme)
    e = sys.exc_info()[1]
    print(e)

    
print("Start Time :" , start , "," , "Finish Time :" , end , "," , "The time required :" , (end - start))
# Close handle
ljm.close(handle)
