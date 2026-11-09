# `pinky_line_alignment/video_replay.py` 사용설명서

**저장 사진·동영상을 같은 조건으로 재생해 검출 결과를 비교합니다.**

## 목차

1. [역할](#역할)
2. [사용 순서](#사용-순서)
3. [입력과 출력](#입력과-출력)
4. [완료 기준과 주의사항](#완료-기준과-주의사항)

## 역할

저장 사진·동영상을 같은 조건으로 재생해 검출 결과를 비교합니다. [원본 파일](../../../../../pinky_line_alignment/video_replay.py)을 확인하세요.

## 사용 순서

python -m pinky_line_alignment.video_replay --input /ABS/PATH/input.avi --output-dir /tmp/pinky-replay-new --methods fixed otsu adaptive --save-video

명령은 저장소 루트의 오프라인 가상환경에서 실행합니다. ROS 노드는 별도의 시스템 Jazzy 환경을 사용합니다.

## 입력과 출력

프레임 CSV, 입력 SHA256·설정·버전 요약, 선택적으로 마스크 PNG와 주석 AVI를 저장합니다.

## 완료 기준과 주의사항

새 출력 폴더를 사용합니다. 실제 촬영 시각과 재생 시각은 다릅니다. 카메라·ROS·모터에 접근하지 않습니다.

[전체 파일 목차](../../../README.md)
