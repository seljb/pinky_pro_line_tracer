# Pinky Pro line alignment — 구현 기록 (2026-11-09)

**Notion 구현 기록의 과거 사본입니다. 현재 GitHub 상태는 실제 브랜치로 확인하며 이 파일은 Notion과 자동 동기화되지 않습니다.**

## 목차

- [이번에 실제로 작성한 코드](#section-1)
- [실제 사용한 오픈소스 / 왜](#section-2)
- [검증된 것과 검증되지 않은 것](#section-3)
- [다음 순서](#section-4)
- [2026-11-09 준비 단계 추가 보완](#section-5)

**대상:** Pinky Pro 부품 자료조사 + Line Tracer 방법 비교. FMS/VDA5050/UI 제외.

**선정:** 보정된 카메라 + 단일 검은 선 중심점들 추출 + 바닥 좌표화 + 오도메트리 기반 **폐루프 회전–이동–회전** + 정렬 완료 검증 + 명시적 인계. 가장 짧은 구현 경로이면서 위치/방향을 각각 검사할 수 있어 기준 방식으로 선택. 근·원거리 영상 서보와 Pure Pursuit는 실측 비교 후 도입 여부 판단.

<a id="section-1"></a>

## 이번에 실제로 작성한 코드

- `vision.py`: ROI, 검은 픽셀 후보, 연결 요소 필터, 영상 여러 행의 중심점, 영상→바닥 좌표 호모그래피, SVD 직선 접선, 횡오차 및 합류점 계산.
- `control.py`: OBSERVE/PLAN 간소화, TURN_TO_TARGET/DRIVE_TO_TARGET/TURN_TO_TANGENT/VERIFY/READY/FAILED 상태. odom 폐루프, 프레임/odom 시효, 시간 초과 시 정지, 재계획 제한.
- `camera_node.py`: `pinkylib.Camera()` 브리지 + 옵션 USB 소스.
- `alignment_node.py`: ROS2 topics/services, 상태 JSON, drive opt-in, handoff_ack.
- `calibration.py`: 내부 카메라 보정 + 실제 바닥 좌표 대응 + **독립 검증점**의 위치 RMSE 확인. `validated` 여부로 실제 명령 차단.
- `offline_demo.py`, `tests/`: 합성 이미지 + 제어기 단위 테스트. **실제 Pinky 동작과 별개**.

<a id="section-2"></a>

## 실제 사용한 오픈소스 / 왜

- PinkLAB `pinky_pro`: `/cmd_vel`, `/odom`, Jazzy bringup 정보로 로봇 구동 인터페이스 확인.
- PinkLAB `pinky_study` wiki: 실제 카메라 라이브러리 기본 API와 보정 교육 방식 참조.
- `gabrielnhn/ros2-line-follower`: ROS2 Image→OpenCV→Twist 구조를 확인, 단일 중심점 제어는 정렬 완료 조건이 되지 못하므로 알고리즘 자체는 재사용하지 않음.
- OpenCV 문서: 카메라 내부/평면 보정의 표준 API 참고.

자세한 주소는 `docs/GITHUB_REFERENCES.md` 참조.

<a id="section-3"></a>

## 검증된 것과 검증되지 않은 것

- 정적 문법 검증과 합성 이미지/순수 Python 단위 테스트는 실행 결과를 남긴 후 상태 기입.
- **실제 로봇 연결, 카메라 FPS·각도·왜곡, 바닥 IR 신호, 최고 속도/모터 지연, 선에 정렬되는 정확도, 소유권 mux 동작**은 미검증.
- 카메라 유효거리 및 IR 검출 방향은 실측 전 공란으로 유지.
- 실물 안전 정지와 외부 속도 명령 mux는 아직 구현하지 않았으므로 단독 실차 주행 불가.

<a id="section-4"></a>

## 다음 순서

1. 실물 토픽·카메라/IR·차축 기준점 조사.
2. 카메라 캘리브레이션과 검은 테이프 반복 촬영, 독립 holdout 오차 측정.
3. 모터 없는 단계에서 이미지/상태 스트림 정상 여부 검증.
4. 하드웨어 비상정지와 명령 mux를 구현하고 통제된 공간에서 저속 폐루프 시험.
5. 최종 위치/각도와 인계 신뢰도 측정 후 단계적 개선.


<a id="section-5"></a>

## 2026-11-09 준비 단계 추가 보완

- **안전 문제 수정:** READY 상태 후 관측 상실/2초 초과 시 FAILED, handoff_ack 직전 선·오도메트리·위치·방향을 재검증.
- **잘못된 데이터 차단:** NaN/Inf 위치·검출 데이터가 있으면 제어하지 않고 FAILED. ROS 헤더에 촬영/발행 시각이 있으면 전송 지연 검사; 값이 없는 메시지는 실제 구동을 거절. 카메라 브리지 수신 시각과 실제 촬영 시각은 구분.
- **모터 출력 제한:** `/cmd_vel` 직접 발행 설정 거부. 안전 mux와 E-stop은 외부에서 구현해야 함.
- **검증 확장:** 16건 오프라인 자동 테스트 통과. 합성 영상+간단한 차동구동 운동학으로 좌/우 ±8cm 출발 시 두 조건 모두 READY. 이 결과는 물리 Pinky Pro의 신뢰성/성공률 증거가 아님.
- **현장용 도구:** `scripts/verify_offline.sh`, `closed_loop_sim.py`, `docs/ROBOT_TEST_CHECKLIST_KO.md`, `logs/experiment_template.csv`, `docs/GITHUB_UPLOAD_PREP_KO.md`.
- **미완료:** 실기기 카메라 촬영 시각, 실제 odom TF, 구동 /cmd_vel mux, IR, 모터 안전 확인 및 실제 GitHub 개인 저장소 생성·업로드.
