# `pinky_line_alignment/camera_node.py` 사용설명서

**Pinky 또는 USB 카메라 영상을 ROS Image로 발행합니다.**

## 목차

1. [파일 역할](#파일-역할)
2. [사용 순서](#사용-순서)
3. [입력과 출력](#입력과-출력)
4. [확인 방법](#확인-방법)
5. [오류와 주의사항](#오류와-주의사항)

## 파일 역할

Pinky 또는 USB 카메라 영상을 ROS Image로 발행합니다. 원본은 [pinky_line_alignment/camera_node.py](../../../../../pinky_line_alignment/camera_node.py)입니다.

주요 진입점: `CameraNode`, `main`.

## 사용 순서

실제 카메라 종류를 확인한 뒤 source:=pinky 또는 source:=usb로 실행하세요.

명령은 별도 표시가 없으면 저장소 루트 `pinky_pro_line_tracer/`에서 실행합니다. Python 명령은 의존성을 설치한 환경에서 실행합니다. ROS 명령은 Jazzy 환경을 source한 터미널에서 실행합니다.

## 입력과 출력

기본 토픽은 /line_align/camera/image_raw, fps 기본값은 10입니다. BGR 3채널을 기대합니다.

## 확인 방법

```bash
ros2 run pinky_line_alignment camera_node --ros-args -p source:=pinky
# USB 장비일 때는 위 명령 대신 다음 명령을 사용한다.
# ros2 run pinky_line_alignment camera_node --ros-args -p source:=usb -p device_index:=0
```
Jazzy와 workspace를 source한 터미널에서 실행합니다. 종료는 Ctrl+C입니다. 생성자 중간 실패에 대한 자원 정리는 아직 별도 보강 대상입니다.

오프라인 확인은 `bash scripts/verify_offline.sh`로 실행합니다. 기존 기준은 16개 시험 통과와 좌·우 합성 시나리오 READY 도달입니다. ROS 노드와 실제 장비 연동은 이 검사에 포함되지 않습니다.

## 오류와 주의사항

헤더 시각은 get_frame 이후 시각이며 실제 노출 시각이 아닙니다. 실제 API와 색상 순서를 확인하세요.

[전체 파일 목차](../../../README.md)
