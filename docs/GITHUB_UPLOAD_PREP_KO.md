# 개인 GitHub 업로드 준비

- 연결 계정으로 확인된 GitHub 사용자: `seljb` (2026-11-09 기준)
- **제안 저장소 이름:** `pinky-pro-line-alignment`
- **소유자:** 개인 계정 `seljb`. `sesac` 조직 계정·기존 `aiot_repo_2` 또는 `local_project`에 업로드하지 않음.
- **현 상태:** 저장소 미생성·commit 미업로드. GitHub 새 저장소를 생성하는 액션이 현재 연결에서 지원되지 않아 보류.
- **공개 범위:** 별도 의사표시가 없다면 `Private` 권장. 라이선스/공개는 사용자 결정에 따름.

## 나중에 새 저장소를 만든 뒤

1. GitHub 사용자 `seljb`로 로그인하고 <https://github.com/new?owner=seljb> 에서 `pinky-pro-line-alignment` 생성.
2. ChatGPT에서 "개인 저장소 만들었어, 업로드해 줘"라고 요청. 새 저장소의 소유자·권한을 확인한 뒤 이 코드의 **실제 커밋 SHA와 업로드 여부**를 기록.
3. 수동 업로드가 필요하면 다음 방식을 사용한다. **반드시 개인 저장소 주소인지 확인 후 실행.** 저장소를 초기화할 때 생성한 README가 있다면 기존 커밋을 먼저 가져오고 덮어쓰기/force push는 하지 않는다.

```bash
# 개인 소유 새 저장소가 GitHub에 생성된 이후에만 실행
# README 없는 빈 저장소를 만들었다는 전제
cd /PATH/TO/pinky_line_alignment
git init -b main
git add .
git commit -m "feat(alignment): add vision-guided line acquisition prototype"
git remote add origin https://github.com/seljb/pinky-pro-line-alignment.git
git push -u origin main
```

**검증 범위:** 업로드할 코드는 오프라인 합성 테스트를 통과했을 뿐, ROS 2 Jazzy 현물 실행과 실제 모터 구동 검증은 미완료다. `.gitignore`가 실측 이미지·보정 파일을 기본 제외한다. 커밋하기 전에 `git status`와 `git diff --cached --stat`을 확인한다.
