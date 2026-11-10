# `pinky_line_alignment/vision.py` 사용설명서

**카메라 영상에서 단일 검은 선의 바닥 위치와 방향을 추정합니다.**

## 목차

1. [파일 역할](#파일-역할)
2. [사용 순서](#사용-순서)
3. [입력과 출력](#입력과-출력)
4. [확인 방법](#확인-방법)
5. [오류와 주의사항](#오류와-주의사항)

## 파일 역할

카메라 영상에서 단일 검은 선의 바닥 위치와 방향을 추정합니다. 원본은 [pinky_line_alignment/vision.py](../../../../../pinky_line_alignment/vision.py)입니다.

주요 진입점: `Calibration`, `LineEstimate`, `LineDetector`.

## 사용 순서

Calibration.load로 보정을 읽고 LineDetector.detect에 BGR 영상을 전달하세요.

명령은 별도 표시가 없으면 저장소 루트 `pinky_pro_line_tracer/`에서 실행합니다. Python 명령은 의존성을 설치한 환경에서 실행합니다. ROS 명령은 Jazzy 환경을 source한 터미널에서 실행합니다.

## 입력과 출력

입력은 보정과 같은 해상도의 영상입니다. 반환은 LineEstimate 또는 검출 실패를 뜻하는 None입니다.

## 확인 방법

```python
from pinky_line_alignment.offline_demo import synthetic_image
from pinky_line_alignment.vision import Calibration, LineDetector

calibration = Calibration.load("config/synthetic_calibration.json")
detector = LineDetector(calibration)
estimate = detector.detect(synthetic_image())
print(estimate)  # 합성 결과 확인용이며 모터 명령이 아니다.
```

오프라인 확인은 `bash scripts/verify_offline.sh`로 실행합니다. 기존 기준은 16개 시험 통과와 좌·우 합성 시나리오 READY 도달입니다. ROS 노드와 실제 장비 연동은 이 검사에 포함되지 않습니다.

## 오류와 주의사항

ROI→연결 영역→행별 중심→바닥 변환→SVD 접선 순서입니다. 교차점·급곡선 처리는 보장하지 않습니다.

[전체 파일 목차](../../../README.md)
