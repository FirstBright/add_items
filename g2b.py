import asyncio
from playwright.async_api import async_playwright
import re
from pathlib import Path
import logging, sys

BASE_DIR = Path(__file__).resolve().parent
LOG_PATH = BASE_DIR / "g2b.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)

log = logging.getLogger(__name__)

GRID_BASE = "mf_wfm_container_tacUntyDtl_contents_tabpSpplItem_body_FUUB059_01_wframe_popupCnts_grdPoup"

async def extract_label_from_popup_grid(page, row_index: int = 0, col_index: int = 3) -> str:
    """
    팝업 그리드의 특정 행/열에서 <nobr class="w2grid_input w2grid_input_readonly"> 텍스트 추출
    기본: 0행 3열 (col_id=dtlsItemClsfNm)
    """
    # 해당 컬럼이 로드됐는지 먼저 컬럼 헤더/바디 존재 대기 (선택)
    try:
        await page.wait_for_selector(f'col#{GRID_BASE}_col_body_{col_index}', timeout=5000)
    except:
        pass  # 헤더 대기 실패해도 바로 셀로 시도

    # 정확한 셀(예: ..._cell_0_3) 안의 nobr 텍스트
    td_sel = f'td#{GRID_BASE}_cell_{row_index}_{col_index} nobr.w2grid_input_readonly'
    try:
        await page.wait_for_selector(td_sel, timeout=5000, state="visible")
        text = await page.locator(td_sel).text_content()
        return (text or "").strip()
    except:
        # fallback: id 패턴이 조금 변주될 경우(동일한 colindex=3만 고정)
        try:
            any_cell_sel = f'td[id^="{GRID_BASE}_cell_"][id$="_{col_index}"] nobr.w2grid_input_readonly'
            await page.wait_for_selector(any_cell_sel, timeout=4000, state="visible")
            text = await page.locator(any_cell_sel).first.text_content()
            return (text or "").strip()
        except:
            return ""

def read_codes(path):
    codes = []
    with open(path, 'r', encoding='utf-8') as f:
        for raw in f:
            line = raw.strip()
            if not line:
                continue
            groups = re.findall(r'\d+', line)
            if not groups:
                continue
            max_len = max(len(g) for g in groups)
            candidates = [g for g in groups if len(g) == max_len]
            codes.append(candidates[-1])
    return codes

async def safe_click(page, selector, *, retries=3, timeout=8000):
    for i in range(retries):
        try:
            await page.wait_for_selector(selector, timeout=timeout, state="visible")
            await page.locator(selector).scroll_into_view_if_needed()
            await page.click(selector, timeout=timeout)
            return True
        except Exception as e:
            if i == retries - 1:
                raise e
            await page.wait_for_timeout(600)
    return False

async def click_save_reliably(page):
    # 저장 버튼 확실히 클릭 + 완료 확인 팝업 처리
    save_sel = 'input#mf_wfm_container_btnM0003'
    await safe_click(page, save_sel, retries=4)

    # 저장 후 나타나는 알림/확인 팝업(패턴 매칭) 처리
    # - 경고/알림/확인 버튼 id 패턴들이 유사하므로 모두 시도
    possible_confirms = [
        '[id^="mf_wfm_container_alert"][id$="_wframe_btnConfirm"]',
        '[id^="mf_wfm_container_confirm"][id$="_wframe_btnYes"]',
        '[id*="_alert"][id$="_wframe_btnConfirm"]',
        '[id*="_confirm"][id$="_wframe_btnYes"]'
    ]
    # 저장 처리 대기
    await page.wait_for_timeout(700)

    for _ in range(2):  # 두 번까지 팝업을 연속 처리 (드물게 안내→확인 연속)
        handled = False
        for sel in possible_confirms:
            try:
                await page.click(sel, timeout=1500)
                handled = True
                await page.wait_for_timeout(400)
            except:
                pass
        if not handled:
            break

    # 네트워크/렌더 안정화
    try:
        await page.wait_for_load_state('networkidle', timeout=6000)
    except:
        pass

async def main():
    with open('id.txt', 'r') as f:
        ids = [line.strip() for line in f.readlines() if line.strip()]
    items = read_codes('items.txt')

    for id_line in ids:
        username, password = id_line.split()
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            page = await browser.new_page()
            screen_size = await page.evaluate('() => ({width: window.screen.width, height: window.screen.height})')
            await page.set_viewport_size(screen_size)
            try:
                await page.goto('https://www.g2b.go.kr/')

                # 오늘하루닫기 체크박스 처리
                try:
                    await page.wait_for_selector('input[title="오늘 하루 이 창을 열지 않음"]', timeout=5000)
                    checkboxes = await page.query_selector_all('input[title="오늘 하루 이 창을 열지 않음"]')
                    for checkbox in checkboxes:
                        await checkbox.click()
                        await page.wait_for_timeout(300)
                except:
                    pass

                # 로그인
                await page.click('a#mf_wfm_gnb_wfm_gnbTop_btnLogin')
                await page.fill('input#mf_wfm_container_tabLgn_contents_content4_body_ibxLgnId', username)
                await page.fill('input#mf_wfm_container_tabLgn_contents_content4_body_ibxLgnPswd', password)
                await page.click('a#mf_wfm_container_tabLgn_contents_content4_body_btnLgn')

                # 보안 안내 팝업 Yes
                try:
                    await page.click('input[id^="mf_wfm_container_tabLgn_contents_content4_body_confirm"][id$="_wframe_btnYes"]', timeout=5000)
                except:
                    pass

                # 조직 선택 더블클릭 (있을 때만)
                try:
                    await page.dblclick('td#mf_wfm_container_tabLgn_contents_content4_body_FUUA003_01_wframe_popupCnts_grdOgdpChc_cell_0_2', timeout=5000)
                except:
                    pass

                # 메뉴 이동
                await page.click('input#mf_wfm_gnb_wfm_gnbMenu_btnSitemap')
                await page.click('a#mf_wfm_gnb_wfm_gnbMenu_genMenu1_7_genMenu2_7_genMenu3_0_btnMenu3')
                await page.click('input#mf_wfm_container_btnU0001A')
                await page.click('a#mf_wfm_container_tacUntyDtl_tab_tabSpplItem_tabHTML')
                await page.click('input#mf_wfm_container_tacUntyDtl_contents_tabpSpplItem_body_btnRowAdd')
                await page.click('input[id^="mf_wfm_container_tacUntyDtl_contents_tabpSpplItem_body_confirm"][id$="_wframe_btnYes"]')

                # 품목 코드 입력 처리
                with open("result.txt", "w", encoding="utf-8") as fout:
                    for item in items:
                        if not item:
                            continue
                        # 검색 입력 후 조회
                        await page.click('input#mf_wfm_container_tacUntyDtl_contents_tabpSpplItem_body_FUUB059_01_wframe_popupCnts_tbxSrchCd___input', timeout=5000)
                        await page.fill('input#mf_wfm_container_tacUntyDtl_contents_tabpSpplItem_body_FUUB059_01_wframe_popupCnts_tbxSrchCd___input', item)
                        await page.click('input#mf_wfm_container_tacUntyDtl_contents_tabpSpplItem_body_FUUB059_01_wframe_popupCnts_btnS0001')

                        # 첫 번째 결과 선택
                        await page.locator('a[onclick*="event.returnValue=false; return false;"]').first.click()

                        # 경고/안내 확인
                        try:
                            await page.click('[id^="mf_wfm_container_tacUntyDtl_contents_tabpSpplItem_body_alert"][id$="_wframe_btnConfirm"]', timeout=3000)
                        except:
                            pass

                        # 화면의 <nobr class="w2grid_input w2grid_input_readonly"> 텍스트 추출 (예: "승강고리")
                        nobr_locator = page.locator('nobr.w2grid_input_readonly')
                        label_text = None
                        try:
                            # 가장 최근/첫 번째 셀 텍스트
                            label_text = await extract_label_from_popup_grid(page, row_index=0, col_index=3)
                            label_text = label_text.strip()
                        except:
                            label_text = ""

                        # 탭으로 구분하여 출력: item \t label
                        fout.write(f"{label_text}\t{item}\n")

                    # 팝업 닫기
                    await page.click('input#mf_wfm_container_tacUntyDtl_contents_tabpSpplItem_body_FUUB059_01_wframe_popupCnts_btnCncl')

                    # 저장(강화)
                    await click_save_reliably(page)

                log.info(f"Successfully processed items for user: {username}")
            except Exception as e:
                log.error(f"Failed to process items for user: {username}", e)
            finally:
                await browser.close()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except Exception:
        logging.exception("Unhandled exception in main()")
        raise