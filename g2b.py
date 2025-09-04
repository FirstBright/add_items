
import asyncio
from playwright.async_api import async_playwright
import re

def extract_item_codes(lines: list[str]) -> list[str]:
    """한 줄에서 연속된 숫자 8~10자리를 추출"""
    results = []
    for line in lines:
        m = re.search(r"\d{8,10}", line)
        if m:
            results.append(m.group())
    return results

def read_lines_any_encoding(path: str) -> list[str]:
    encodings = ["utf-8-sig", "utf-8", "cp949", "euc-kr", "latin-1"]
    for enc in encodings:
        try:
            with open(path, "r", encoding=enc, errors="strict") as f:
                return [line.strip() for line in f if line.strip()]
        except UnicodeDecodeError:
            continue
    # 마지막 안전망: 손실 허용
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return [line.strip() for line in f if line.strip()]

async def main():
    ids = read_lines_any_encoding("id.txt")
    raw_items = read_lines_any_encoding("items.txt")
    items = extract_item_codes(raw_items)

    for id_line in ids:
        username, password = id_line.split()
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            page = await browser.new_page()
            screen_size = await page.evaluate('() => ({width: window.screen.width, height: window.screen.height})')
            await page.set_viewport_size(screen_size)
            try:
                await page.goto('https://www.g2b.go.kr/')

                try:
                    await page.wait_for_selector('input[title="오늘 하루 이 창을 열지 않음"]', timeout=5000)
                    checkboxes = await page.query_selector_all('input[title="오늘 하루 이 창을 열지 않음"]')
                    for checkbox in checkboxes:
                        await checkbox.click()
                        await page.wait_for_timeout(500)
                except:
                    pass
                await page.click('a#mf_wfm_gnb_wfm_gnbTop_btnLogin')
                await page.fill('input#mf_wfm_container_tabLgn_contents_content4_body_ibxLgnId', username)
                await page.fill('input#mf_wfm_container_tabLgn_contents_content4_body_ibxLgnPswd', password)
                await page.click('a#mf_wfm_container_tabLgn_contents_content4_body_btnLgn')

                try:
                    await page.click('input[id^="mf_wfm_container_tabLgn_contents_content4_body_confirm"][id$="_wframe_btnYes"]', timeout=5000)
                except:
                    pass

                try:
                    await page.dblclick('td#mf_wfm_container_tabLgn_contents_content4_body_FUUA003_01_wframe_popupCnts_grdOgdpChc_cell_0_2', timeout=5000)
                except:
                    pass
                await page.click('input#mf_wfm_gnb_wfm_gnbMenu_btnSitemap')
                await page.click('a#mf_wfm_gnb_wfm_gnbMenu_genMenu1_7_genMenu2_7_genMenu3_0_btnMenu3')
                await page.click('input#mf_wfm_container_btnU0001A')
                await page.click('a#mf_wfm_container_tacUntyDtl_tab_tabSpplItem_tabHTML')
                await page.click('input#mf_wfm_container_tacUntyDtl_contents_tabpSpplItem_body_btnRowAdd')
                await page.click('input[id^="mf_wfm_container_tacUntyDtl_contents_tabpSpplItem_body_confirm"][id$="_wframe_btnYes"]')
           
                for item in items:
                    if item:
                        await page.click('input#mf_wfm_container_tacUntyDtl_contents_tabpSpplItem_body_FUUB059_01_wframe_popupCnts_tbxSrchCd___input', timeout=5000)
                        await page.fill('input#mf_wfm_container_tacUntyDtl_contents_tabpSpplItem_body_FUUB059_01_wframe_popupCnts_tbxSrchCd___input', item)
                        await page.click('input#mf_wfm_container_tacUntyDtl_contents_tabpSpplItem_body_FUUB059_01_wframe_popupCnts_btnS0001')
                        await page.locator('a[onclick*="event.returnValue=false; return false;"]').first.click()
                        try:
                            await page.click('[id^="mf_wfm_container_tacUntyDtl_contents_tabpSpplItem_body_alert"][id$="_wframe_btnConfirm"]', timeout=5000)
                        except:
                            pass

                await page.click('input#mf_wfm_container_tacUntyDtl_contents_tabpSpplItem_body_FUUB059_01_wframe_popupCnts_btnCncl')
                await page.click('input#mf_wfm_container_btnM0003')

                print(f'Successfully processed items for user: {username}')
            except Exception as e:
                print(f'Failed to process items for user: {username}', e)
            finally:
                await browser.close()

if __name__ == '__main__':
    asyncio.run(main())
