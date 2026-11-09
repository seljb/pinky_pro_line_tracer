# Pinky Pro — 카메라 기반 검은 선 합류·정렬 (ROS 2 Jazzy)

> **현재 단계:** 소스코드 + 오프라인 테스트. Pinky Pro 실물 검증 **미완료**. 배포용 안전 제어기가 아니다.

## 이번 범위

1. Pinky Pro 전면 카메라 영상에서 **흰 바닥 위 검은 단일선** 검출.
2. **실측한 카메라 내부 보정 + 영상→로봇 바닥 좌표 변환**으로 선의 횡위치/방향 계산.
3. `OBSERVE → TURN_TO_TARGET → DRIVE_TO_TARGET → TURN_TO_TANGENT → VERIFY → READY`의 **저속 폐루프 정렬**.
4. 선이 사라짐, 카메라/오도메트리 갱신 중단, 시간 초과 시 정지/실패 표시.
5. 타 라인트레이싱 담당자가 명시적으로 준비됐음을 알리고 인계 확인. **속도 명령의 실제 소유권 전환은 외부 mux가 해야 함.**

**범위 밖:** FMS, VDA 5050, 선 전체 추종, 충돌 방지/비상정지, 장애물 처리, 선 교차점 선택, 전역 경로 최적화, 검증되지 않은 현물 정격.

## 파일 구조

```text
pinky_line_alignment/
├── pinky_line_alignment/
│   ├── vision.py             # 실측 보정/검은 선 인식/바닥 좌표 추정
│   ├── control.py            # 상태기계와 오도메트리 기반 회전-이동-회전 제어
│   ├── alignment_node.py     # ROS2 구독/진단/서비스/속도 출력
│   ├── camera_node.py        # pinkylib.Camera -> ROS Image 브리지
│   ├── calibration.py        # 체커보드/평면 보정과 독립 검증
│   └── offline_demo.py       # ROS·실물 없이 합성영상으로 동작 점검
├── config/                   # 예시값/합성값. 실물값 아님
├── tests/                    # 오프라인 자동 테스트
└── docs/GITHUB_REFERENCES.md # 어떤 오픈소스를 왜 참고했는지
```

## 1. 로봇 없이 먼저 테스트 (Ubuntu / Python 3.12)

```bash
cd pinky_line_alignment
python3 -m venv .venv
source .venv/bin/activate
pip install numpy opencv-python pytest
python -m pytest -q
python -m pinky_line_alignment.offline_demo --output /tmp/pinky_alignment_preview.png
python -m pinky_line_alignment.closed_loop_sim
```

오프라인 이미지는 **가상의 평면 카메라**를 가정하며 실물 정확도 증거가 아니다. 실제로는 `ros2` Python 환경에 `rclpy`, `cv_bridge` 등이 설치되어야 한다. 시스템 ROS 2를 사용할 때 별도의 일반 pip venv를 섞지 않는 것이 안전하다.

## 2. Pinky 실물 정보 확인 (아직 실제 장비에서 실행하지 않음)

```bash
source /opt/ros/jazzy/setup.bash
ros2 topic list -t
ros2 node list
ros2 topic info /cmd_vel -v
ros2 topic info /odom -v
ros2 topic hz /odom
python3 -c 'from pinkylib import Camera; print("pinkylib imported")'
```

- 공식 [pinky_pro](https://github.com/pinklab-art/pinky_pro)에는 Ubuntu 24.04 / ROS 2 Jazzy bringup 예제가 있음.
- 공개 bringup 드라이버는 `Twist /cmd_vel`을 받고 `Odometry /odom`을 내보내는 구조임. **보유한 로봇에서 실제 경로·토픽·QoS를 확인**해야 함.
- [Pinky 교육 카메라 자료](https://github.com/pinklab-art/pinky_study/wiki/2.2-Pinky-Pro(part2))에는 `Camera().start()`, `get_frame()`, `close()` 사용 예제가 있음. `pinky` backend가 설치되지 않았다면 USB 대체 입력이 가능함.
- IR 3개는 현재 코드에서 **활성화하지 않았음**. 바닥을 실제로 검출하는지, 극성·물리 순서·시점이 맞는지 실측한 뒤 검증 보조에만 추가할 것.

## 3. 실제 카메라 보정 절차 (필수)

최소 측정: 실제 camera mode, 이미지 크기, 렌즈/왜곡, 바닥 좌표계, 카메라 고정, 밝기/그림자 시험.

1. 바닥 앞쪽에 **실제 크기를 측정한** 체커보드를 다각도에서 8장 이상 촬영하고 이미지 경로를 준비한다.
2. 예제 내부 코너가 8×6, 칸 길이가 0.025 m인 **경우에만** 다음 명령을 쓴다.

```bash
python -m pinky_line_alignment.calibration intrinsic \
  --glob 'calib_img/*.jpg' --cols 8 --rows 6 --square-m 0.025 \
  --output intrinsics.json
```

3. 사용 중인 카메라 이미지의 **왜곡 보정된 영상**에서 픽셀 위치와 바닥의 실측 `(x forward, y left)` 값을 대응한다. `config/floor_pairs_example.json`은 **형식 예제일 뿐**이며 숫자는 사용하면 안 된다. 최소 4점보다 많은 점을 권장하며 넓게 배치하고 별도의 검증점 5개 이상을 남긴다.
4. 위 대응점을 `measured_floor_pairs.json`으로 만든 뒤:

```bash
python -m pinky_line_alignment.calibration floor \
  --pairs measured_floor_pairs.json \
  --intrinsics intrinsics.json --output real_calibration_unverified.json
```

5. 위에 **사용하지 않은 독립 검증점**들을 `measured_holdout.json`으로 기록한 뒤:

```bash
python -m pinky_line_alignment.calibration validate \
  --calibration real_calibration_unverified.json \
  --holdout measured_holdout.json --rmse-max-m 0.015 --mark-valid \
  --output real_calibration.json
```

`0.015 m`는 **개발 중 임시 검증 한계**이며 실제 선 폭·성공 기준으로 조정해야 한다. 내부 RMSE만 낮다고 안전한 주행이 보증되지는 않는다. 사용한 체커보드, 포즈, 조명, 카메라 고정 상태를 별도 기록할 것.

## 4. ROS 2 빌드

ROS 2 Jazzy 환경에서 `pinky_line_alignment` 폴더를 workspace `src`에 복사한다.

```bash
sudo apt update
sudo apt install python3-opencv python3-numpy python3-pytest \
  ros-jazzy-rclpy ros-jazzy-cv-bridge ros-jazzy-sensor-msgs \
  ros-jazzy-nav-msgs ros-jazzy-geometry-msgs ros-jazzy-std-msgs \
  ros-jazzy-std-srvs python3-colcon-common-extensions
source /opt/ros/jazzy/setup.bash
mkdir -p ~/pinky_ws/src
# ./pinky_line_alignment 폴더를 ~/pinky_ws/src/ 아래에 복사
cd ~/pinky_ws
colcon build --packages-select pinky_line_alignment --symlink-install
source install/setup.bash
```

## 5. 카메라 브리지 + 모니터링 실행 (모터 **OFF**, 권장 시작)

터미널 1: 실제 Pinky/PC에서 로봇 bringup과 `/odom`을 준비한 뒤:

```bash
ros2 run pinky_line_alignment camera_node --ros-args -p source:=pinky
# pinkylib가 없다면, 카메라를 USB로 연결한 환경에서 -p source:=usb -p device_index:=0
```

터미널 2: 로봇은 움직이지 않고 카메라 검출만 점검:

```bash
ros2 run pinky_line_alignment alignment_node --ros-args \
  -p calibration_file:=/ABS/PATH/real_calibration.json \
  -p camera_topic:=/line_align/camera/image_raw \
  -p odom_topic:=/odom \
  -p allow_drive:=false
```

터미널 3:

```bash
ros2 topic echo /line_align/status
ros2 topic echo /line_align/ready
ros2 topic hz /line_align/camera/image_raw
```

카메라 해상도와 보정 JSON 크기가 다르면 오류를 출력하고 **정렬 시작이 되지 않음**.

## 6. 실제 바퀴 구동 시험 (현장 안전 확인 후에만)

**먼저:** 높이·렌즈·바닥 보정 측정, 모터 방향 및 odom 확인, 장애물이 없는 시험장, 차체를 들어 올린 시험, 독립 하드웨어 비상정지, 실제 `/cmd_vel` 단일 제어자 확인. 다른 추종기/Nav2/teleop와 모터 제어를 동시에 하지 않음. 실제 로봇이 임의로 회전할 수 있으므로 안전 공간 확보.

기본 속도 출력은 `/line_align/cmd_vel`이므로 실제 구동은 **외부 명령 선택기(mux)와 인터록을 안전하게 구성한 뒤** 연결해야 한다. mux는 안전정지와 control ownership을 보장해야 하며 이 예제에는 포함하지 않았다.

```bash
ros2 run pinky_line_alignment alignment_node --ros-args \
  -p calibration_file:=/ABS/PATH/real_calibration.json \
  -p cmd_vel_topic:=/line_align/cmd_vel -p allow_drive:=true

# 검증된 mux 환경에서만, 다음 서비스로 시작
ros2 service call /line_align/start std_srvs/srv/Trigger '{}'

# 언제든 정지 요청(모터 비상 정지 수단은 별도로 마련)
ros2 service call /line_align/stop std_srvs/srv/Trigger '{}'
```

실제 명령 소유자 전환은 mux 책임이다. `READY`는 정렬 모듈이 정지를 유지하는 상태일 뿐, 뒤따르는 추종 노드가 자동으로 구동한다는 뜻이 아니다. `/line_follower/ready` `std_msgs/Bool` **신선한 true**가 들어온 뒤:

```bash
ros2 service call /line_align/handoff_ack std_srvs/srv/Trigger '{}'
```

실제 인계 시 mux를 전환하는 구현은 별도 필요하다. 서비스 호출 자체가 `/cmd_vel` 전환이나 로봇 안전성을 보장하지 않는다.

## 7. 다음 실측 및 한계

- 시험 전: **검은 테이프 폭**, 반사율, 카메라/IR 실제 유효 거리와 장착 방향, 모터/odom 지연, 시작 범위, 스캔 경계, 경로의 곡률, 목표 허용오차를 측정한다.
- 초기 구현은 **단일 연결된 선, 직선~완만한 곡선**, 충분히 보이는 선에 한정. 교차점, 급곡선, 수평에 가까운 화면상 선, 큰 시야 손실은 미지원/안전 정지 대상이다.
- 카메라를 회전시키면 선이 시야 밖으로 나갈 수 있다. 초기 버전은 **관측 상실 시 정지**하고 자동 무한 탐색하지 않는다. 후속 단계에서 짧은 오도메트리 fallback을 검증해 추가한다.
- 화면 한 줄의 중심점보다 여러 점을 바닥 좌표로 옮기지만 현재는 주성분 직선 접선 근사다. 급곡선은 국소 곡선 모델 추가가 필요.
- `0.05 m/s`, `0.35 rad/s`, 15mm 횡오차, 6° 방위 오차 등의 값은 **일시적 시작값**이지 검증된 Pinky Pro 성능/안전 기준이 아니다.
- READY 상태는 **2초 이내에 인계하지 않거나 관측값이 사라지면 FAILED로 전환**된다. READY만 믿고 추종기 모터를 구동하지 않는다.
- 직접 `/cmd_vel`을 출력하는 설정은 금지된다. 실제 구동에는 외부 명령 선택기(mux)가 반드시 필요하다.
- ROS 메시지 헤더가 있으면 전송 지연을 검사하지만 **카메라 촬영 시각이 아니라 get_frame 이후 찍은 시각일 수 있음**. 카메라 실제 촬영 지연은 별도 측정해야 한다.
- 카메라 소비 파이프라인과 하드웨어 모터 제어를 PC에서 재현하지 않았으므로, 여기서 테스트 성공은 **알고리즘 단위 테스트**에만 해당한다.

## 8. 참고 GitHub / 라이선스

[docs/GITHUB_REFERENCES.md](docs/GITHUB_REFERENCES.md) 참조. 이번 소스는 참고 코드의 복제가 아니라 새로 작성한 구현이다. 외부 저장소의 소스 파일을 통째로 포함하지 않았다.

## 9. 설치 전에 확인할 다음 실험

실물 연결 절차는 [docs/ROBOT_TEST_CHECKLIST_KO.md](docs/ROBOT_TEST_CHECKLIST_KO.md), 기록 양식은 [logs/experiment_template.csv](logs/experiment_template.csv) 참조.
단위 테스트에 더해 합성 카메라 + 이상적인 차동구동 오도메트리 결합 시뮬레이터를 추가했지만 이것도 실차 결과는 아니다.
