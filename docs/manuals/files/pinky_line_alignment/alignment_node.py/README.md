# `pinky_line_alignment/alignment_node.py` 사용설명서

**ROS 이미지·odom·서비스를 정렬 제어기에 연결합니다.**

## 목차

1. [파일 역할](#파일-역할)
2. [사용 순서](#사용-순서)
3. [입력과 출력](#입력과-출력)
4. [확인 방법](#확인-방법)
5. [오류와 주의사항](#오류와-주의사항)

## 파일 역할

ROS 이미지·odom·서비스를 정렬 제어기에 연결합니다. 원본은 [pinky_line_alignment/alignment_node.py](../../../../../pinky_line_alignment/alignment_node.py)입니다.

주요 진입점: `AlignNode`, `main`.

## 사용 순서

실측 보정 파일을 준비하고 allow_drive:=false로 시작하세요.

명령은 별도 표시가 없으면 저장소 루트 `pinky_pro_line_tracer/`에서 실행합니다. Python 명령은 의존성을 설치한 환경에서 실행합니다. ROS 명령은 Jazzy 환경을 source한 터미널에서 실행합니다.

## 입력과 출력

상태 /line_align/status, 준비 /line_align/ready, 디버그 영상과 별도 속도 토픽을 발행합니다.

## 확인 방법

```bash
source /opt/ros/jazzy/setup.bash
source ~/pinky_ws/install/setup.bash
ros2 run pinky_line_alignment alignment_node --ros-args \
  -p calibration_file:=/ABS/PATH/real_calibration.json \
  -p allow_drive:=false
```
`/ABS/PATH/...`는 실제 생성한 보정 파일의 절대경로로 교체합니다. 기본 camera/odom 토픽이 장비와 다르면 파라미터로 지정합니다. 이 예시는 모터 OFF 모니터링용입니다.

오프라인 확인은 `bash scripts/verify_offline.sh`로 실행합니다. 기존 기준은 16개 시험 통과와 좌·우 합성 시나리오 READY 도달입니다. ROS 노드와 실제 장비 연동은 이 검사에 포함되지 않습니다.

## 오류와 주의사항

기본 출력도 0 Twist를 발행하므로 외부 mux 연결을 확인하세요. /cmd_vel 직접 설정 차단만으로 안전 소유권이 보장되지 않습니다.

[전체 파일 목차](../../../README.md)
