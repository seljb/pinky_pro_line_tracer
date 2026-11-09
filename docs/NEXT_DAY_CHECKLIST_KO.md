# 2026-11-11 노트북 작업 목록

**내일의 우선 목표는 코드 수령·오프라인 검증·ROS 빌드·모터 OFF 센서 확인입니다.** 카메라 보정과 외부 mux·독립 비상정지 검증이 끝나기 전에는 주행하지 않습니다. 날짜는 이 대화의 한국 시간 기준입니다.

## 목차

1. [준비와 코드 수령](#준비와-코드-수령)
2. [오프라인 테스트](#오프라인-테스트)
3. [ROS 빌드](#ros-빌드)
4. [모터 OFF 센서 확인](#모터-off-센서-확인)
5. [보정과 인식 점검](#보정과-인식-점검)
6. [조건부 후속 시험](#조건부-후속-시험)
7. [기록과 종료](#기록과-종료)

## 준비와 코드 수령

- [ ] 노트북·Pinky Pro·전원·카메라 연결 장비를 준비합니다.
- [ ] `lsb_release -ds`, `python3 --version`으로 Ubuntu 24.04 / Python 3.12 여부를 기록합니다.
- [ ] 실제 모터 전원을 비활성화하고 기존 teleop·추종기·Nav2 실행 여부를 확인합니다. 소프트웨어 옵션만 믿지 않습니다.
- [ ] 아래 명령으로 기능 브랜치를 받습니다. 이미 clone했다면 새 clone 대신 기존 폴더에서 `git status`로 변경사항을 확인한 뒤 fetch·switch·pull을 진행합니다. 작업 파일을 덮어쓰거나 reset하지 않습니다.

```bash
mkdir -p ~/pinky_ws/src
cd ~/pinky_ws/src
git clone --branch feat/video-validation https://github.com/seljb/pinky_pro_line_tracer.git
cd pinky_pro_line_tracer
git branch --show-current
git log -1 --oneline
```

**완료 기준:** 브랜치가 `feat/video-validation`이고 최신 문서가 보입니다. `main`은 직접 push하지 않습니다.

## 오프라인 테스트

- [ ] 저장소 루트에서 ROS 환경과 분리한 가상환경을 만듭니다.
- [ ] 의존성을 설치하고 기존 오프라인 검증 스크립트를 실행합니다.
- [ ] 테스트 수·실패 내용·좌우 합성 정렬 상태를 기록합니다.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m black --check .
bash scripts/verify_offline.sh
deactivate
```

`venv` 생성이 실패하면 Ubuntu의 `python3-venv` 설치 여부를 확인합니다. 패키지 설치 실패를 무시하고 다음 단계로 넘어가지 않습니다.

**완료 기준:** 2026-11-10 새 브랜치 기준 189개 시험 통과, 합성 좌·우 8cm 조건에서 READY입니다. 합성 성공은 실제 주행 성공이 아닙니다. formatter는 동작 시험을 대신하지 않습니다.

새 영상 도구 사용법과 합성 검증은 [영상 검증 안내](VIDEO_VALIDATION_KO.md)를 함께 확인합니다. 새 브랜치는 기존 정렬 기능을 포함하면서 재생·명령 선택 검증을 추가합니다.

## ROS 빌드

- [ ] 일반 pip 가상환경을 종료한 새 터미널에서 ROS 2 Jazzy 환경을 활성화합니다.
- [ ] `rclpy`, `cv_bridge`, ROS 메시지 패키지, `python3-opencv`, `python3-numpy`, colcon을 준비합니다. 설치 명령은 [루트 안내](../README.md)의 ROS 빌드 절을 따릅니다.
- [ ] workspace에서 대상 패키지만 빌드합니다.

```bash
source /opt/ros/jazzy/setup.bash
cd ~/pinky_ws
colcon build --packages-select pinky_line_alignment --symlink-install
source install/setup.bash
ros2 pkg executables pinky_line_alignment
```

**완료 기준:** 빌드가 종료 코드 0으로 끝나고 `camera_node`, `alignment_node` 등 진입점이 조회됩니다. `/opt/ros/jazzy/setup.bash`가 없으면 Jazzy 설치부터 해결합니다. 클라우드에서 ROS 빌드가 검증됐다고 가정하지 않습니다.

## 모터 OFF 센서 확인

- [ ] 공식 장비 절차로 센서/bringup을 준비하되 모터 전원은 계속 비활성화합니다.
- [ ] `ros2 topic list -t`, `ros2 node list`로 실제 인터페이스를 확인합니다.
- [ ] `ros2 topic info /cmd_vel -v`로 발행자와 구독자를 확인합니다. 모터 OFF이어도 기존 명령 발행자를 기록합니다.
- [ ] `ros2 topic info /odom -v`, `ros2 topic hz /odom`으로 타입·QoS·갱신 주기를 확인합니다. 출력 확인 후 Ctrl+C로 종료합니다.
- [ ] `odom`/`base_link`, 거리 단위·회전 부호·헤더 시각을 확인합니다.
- [ ] `python3 -c 'from pinkylib import Camera; print("pinkylib imported")'`로 import를 확인합니다. 성공해도 실제 촬영 성공을 뜻하지 않습니다.
- [ ] 실제 소스에 맞춰 아래 명령 중 하나만 실행합니다. USB에서는 장치 번호를 실측합니다.

```bash
ros2 run pinky_line_alignment camera_node --ros-args -p source:=pinky
# USB인 경우 위 명령 대신 실행
# ros2 run pinky_line_alignment camera_node --ros-args -p source:=usb -p device_index:=0
```

- [ ] 다른 ROS 터미널에서 `ros2 topic hz /line_align/camera/image_raw`로 갱신을 확인합니다.
- [ ] 영상 해상도·BGR/RGB 순서·노출·실제 프레임 지연을 기록합니다. 브리지 헤더는 촬영 시각이 아닌 수신 후 시각일 수 있습니다.

**완료 기준:** 실제 영상과 odom이 확인되고 오류·결측·미확인 사항을 기록했습니다. IR 센서는 현재 코드에서 사용하지 않습니다.

## 보정과 인식 점검

- [ ] 실제 카메라 해상도와 장착 위치를 고정합니다.
- [ ] 실측 체커보드로 다양한 자세의 이미지 8장 이상을 준비합니다.
- [ ] 내부 보정 → 바닥 대응점 → 독립 검증점 순서로 [보정 안내](../README.md)를 수행합니다.
- [ ] 대응점은 최소 4개 비공선 점(6개 이상 권장), 독립 검증점은 보정에 쓰지 않은 점 5개 이상을 사용합니다.
- [ ] 예시 JSON의 숫자를 실측값으로 사용하거나 `validated`를 수동으로 true로 바꾸지 않습니다.
- [ ] 아래 명령의 경로를 실제 생성한 파일의 절대경로로 바꾸고 실행합니다. 파일이 없으면 먼저 보정을 수행합니다.

```bash
ros2 run pinky_line_alignment alignment_node --ros-args \
  -p calibration_file:=/ABS/PATH/real_calibration.json \
  -p allow_drive:=false
```

- [ ] 다른 터미널에서 `ros2 topic echo /line_align/status`로 선 검출과 odom 상태를 확인합니다.
- [ ] 선 좌우 이동·각도 변화에서 오차 부호가 실제 방향과 일치하는지 확인합니다.
- [ ] 선 없음·그림자·해상도 불일치·입력 중단 때 진단 변화를 기록합니다.

**완료 기준:** 인식 오차와 보정 근거가 기록됐습니다. `allow_drive:=false`에서는 start 서비스가 거절되는 것이 정상이며, IDLE에서 관측 상실은 무조건 FAILED로 전이하는 것이 아닙니다. READY 중 센서 손실·인계 거부의 실물 검증은 별도 단계입니다.

## 조건부 후속 시험

- [ ] 독립 하드웨어 비상정지, 외부 명령 mux, 단일 명령 소유권을 실제 검증했는지 확인합니다.
- [ ] 실제 구동 속도·모터 방향·odom·전송 지연·공간 안전을 확인합니다.
- [ ] 조건을 모두 충족한 뒤에만 별도 주행 시험을 계획합니다. **내일 체크리스트를 끝내려고 구동을 강행하지 않습니다.**
- [ ] 실제 인계 시험에서는 follower의 fresh ready, READY 만료와 센서 손실 시 거부, mux 소유권 전환을 각각 검사합니다. handoff_ack 성공만으로 실제 전환 성공을 기록하지 않습니다.

## 기록과 종료

- [ ] `logs/experiment_template.csv`를 별도 파일로 복사해 환경·결과·실패 이유를 기록합니다. 날짜·거리·각도·지연 단위를 유지합니다.
- [ ] 미실시·실패·성공을 구분하고 실측 이미지와 보정 파일을 Git에 올리지 않습니다.
- [ ] 직접 시작한 노드를 Ctrl+C로 종료하고 장치 자원·모터 전원 상태를 확인합니다.
- [ ] 변경사항은 영문 `type(scope)` 커밋 → 기능 브랜치 push → PR → 팀원 리뷰로 진행합니다.
- [ ] Notion 연결이 제공되면 이 문서의 체크리스트를 옮깁니다. 현재 저장소 문서는 Notion과 자동 동기화되지 않습니다.

[파일별 사용설명서](manuals/README.md) · [실물 상세 점검표](ROBOT_TEST_CHECKLIST_KO.md)
