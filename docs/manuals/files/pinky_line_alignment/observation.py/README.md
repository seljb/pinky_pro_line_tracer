# `pinky_line_alignment/observation.py` 사용설명서

**픽셀 공간에서 검은 테이프 후보를 관찰하고 모호한 경로를 거부합니다.**

## 목차

1. [역할](#역할)
2. [사용 순서](#사용-순서)
3. [입력과 출력](#입력과-출력)
4. [완료 기준과 주의사항](#완료-기준과-주의사항)

## 역할

픽셀 공간에서 검은 테이프 후보를 관찰하고 모호한 경로를 거부합니다. [원본 파일](../../../../../pinky_line_alignment/observation.py)을 확인하세요.

## 사용 순서

ObservationConfig와 PixelLineTracker를 생성하고 BGR uint8 영상과 단조 증가하는 시각(초)을 process에 전달합니다.

명령은 저장소 루트의 오프라인 가상환경에서 실행합니다. ROS 노드는 별도의 시스템 Jazzy 환경을 사용합니다.

## 입력과 출력

FrameAnalysis의 마스크·행별 중심·error_px·valid·reason을 반환합니다. m·rad·속도는 생성하지 않습니다.

## 완료 기준과 주의사항

fixed/Otsu/adaptive, ROI, 필터, 연결 성분과 양측 밝기 대비를 비교합니다. 모든 코너·그림자·검은 물체를 식별하는 분류기는 아닙니다.

[전체 파일 목차](../../../README.md)
