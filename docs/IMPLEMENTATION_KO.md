# Pinky Pro 선 합류·정렬 구현 기록

작성: 2026-11-09 / 상태: 합성 데이터 단위 테스트 완료, ROS2 실차 테스트 미진행

## 목표와 범위

흰 바닥 검은 선 바깥에서 출발하는 Pinky Pro의 A 기능을 구현한다. 카메라로 선을 인식하고 선 중심 위치와 진행 방향을 추정한 뒤 폐루프 회전→이동→회전으로 정렬해 READY 상태를 만든다. B 선 추종과의 제어권 인계는 별도 검증 필요. FMS/VDA5050 제외.

## 선정 이유

노션 Line Tracer 방법 비교에서 첫 구현 추천은 카메라 + 실제 바닥 보정 + 회전–이동–회전 + 검증 + 인계 상태기계. 카메라 한 점 PID만으로 차체 방향과 선 중심 위치를 함께 보증할 수 없으며, Pure Pursuit는 기준 방식에서 시간 병목을 확인한 후 도입.

## 구현 파일과 역할

- `vision.py`: 카메라 왜곡 보정, 바닥 ROI, 어두운 연결 영역, 여러 중심점, 호모그래피, 바닥 접선과 오차 추정.
- `control.py`: OBSERVE → TURN_TO_TARGET → DRIVE_TO_TARGET → TURN_TO_TANGENT → VERIFY → READY/FAILED. odom 폐루프, 관측 끊김·시효·타임아웃 정지.
- `alignment_node.py`: ROS 2 Image/Odometry 수신, status 발행, start/stop 서비스. 기본 모터 비활성화. READY에서 속도 0. 실제 B와 제어권 mux 연결 전 handoff_ack 거부.
- `camera_node.py`: USB 카메라 OpenCV 또는 pinkylib 카메라 브리지(실기기 API 확인 필수).
- `calibration.py`: 실측 영상·바닥 점을 이용한 호모그래피 계산, 자동 검증되지 않은 값으로 저장.
- `offline_demo.py`: 합성선 검출.
- `tests`: 시작/센서 시효/프레임별 완료 검증/검출 테스트.

## 시험 결과

`python -m pytest -q` → **16 passed** (합성·순수 Python 단위 시험). `python -m pinky_line_alignment.offline_demo` → 선 추정 출력 및 이미지 파일 생성. `python -m pinky_line_alignment.closed_loop_sim` → 좌우 8cm 시작 조건의 합성 카메라+오도메트리 폐루프 READY 확인 (이상적인 조건, 실물 검증 아님). ROS2/실제 센서·모터 연결 시험은 실시하지 않음.

## GitHub 출처: 무엇을, 어떻게, 왜 활용했는가

| 자료 | 읽은 내용 | 선택 이유/실제 활용 |
| --- | --- | --- |
| [PinkLAB pinky_pro 구동 코드](https://github.com/pinklab-art/pinky_pro/blob/main/pinky_bringup/pinky_bringup/bringup.py) | `cmd_vel`의 Twist, `odom`의 Odometry, 구동부 차동 운동학 | 공식 ROS2 토픽을 확인해 어댑터 메시지 형식을 설계. 구동 코드 자체는 복사하지 않음 |
| [PinkLAB bringup launch](https://github.com/pinklab-art/pinky_pro/blob/main/pinky_bringup/launch/bringup_robot.launch.xml) | 실제 bringup 구성에 카메라 퍼블리셔가 명시되지 않음 | 카메라 입력 어댑터를 별도로 구성 |
| [Pinky Pro 카메라 교육](https://github.com/pinklab-art/pinky_study/wiki/2.2-Pinky-Pro(part2)) | 카메라 보정 안내, pinkylib 개념 | 실측 보정이 필수임을 설계에 반영; 현물 API 및 출력 채널 순서는 확인 필요 |
| [gabrielnhn ROS2 line follower](https://github.com/gabrielnhn/ros2-line-follower) | ROS 영상→검출→Twist 형태의 경량 구조 | 구조 참고. 단일 중심점 기반 제어는 정렬 목적에 부족하여 복사하지 않음 |
| [OpenCV 호모그래피 공식 문서](https://docs.opencv.org/4.x/d9/dab/tutorial_homography.html) | 평면 좌표 변환 | 로봇 좌표계의 거리·방향을 추정하는 기하 처리에 활용 |

GitHub 계정 `seljb` 연결 확인. 개인 저장소에 새 브랜치/커밋/푸시는 하지 않았음(대상 저장소·브랜치 미지정). 출처는 읽기 전용 사용.

## 아직 완료되지 않은 부분

1. 실제 Pinky Pro의 카메라 API, pixel format, frame.shape, frame ID 및 실제 ROS2 `odom` 시각/주기 검증.
2. 실물 내부 보정값 K/D + 바닥 대응점 H + 독립 검증 오차 산출. 템플릿 값은 실제 이동에 사용 불가.
3. IR 바닥 방향/장착 높이·검은 선 반응 측정, 필요할 경우 보조 검증 로직 추가.
4. 장애물 감시, 물리 비상 정지, cmd_vel 소유권 mux, B follower-ready 확인 및 안전한 handoff 구현.
5. 카메라 시간동기와 지연 측정, 급격한 곡률·교차로·그림자·선 손실 실물 검증.
6. 현물 정렬 성공률·횡오차·방향오차·시간·CPU·메모리 측정 후 개선 후보(Pure Pursuit)와 비교.

## 실행 명령(모터 연결 없이 우선 검증)

```bash
cd pinky_line_alignment
python3 -m pytest -q
python3 -m pinky_line_alignment.offline_demo
```

ROS2 Jazzy 설치 후 `README.md`의 colcon 절차를 따르고, 기본 `allow_drive:=false`로 상태만 관찰한다. 실제 모터 테스트는 외부 안전 장치 및 수동 검증 후 별도 시행.
