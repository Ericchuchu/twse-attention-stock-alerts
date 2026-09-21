import requests
import time
import re
import os
import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from webdriver_manager.microsoft import EdgeChromiumDriverManager
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import telebot
import datetime
import os
import ssl

ssl._create_default_https_context = ssl._create_unverified_context

#telegram bot (credentials come from the environment, see .env.example)
API_key=os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID=int(os.environ["TELEGRAM_CHAT_ID"])
bot=telebot.TeleBot(API_key)
next_month='0'
'''
@bot.message_handler(commands=['start','help'])
def handle_start_help(message):
    print(message.chat.id)

bot.polling()
'''
retry_count = 0
def main(past_stock_number):
    #字典寫入list的function
    global retry_count
    def append_revenue(stock,current_revenue,average_revenue_last_season):
        revenue_dict={}
        revenue_dict['股票']=stock
        revenue_dict['最近一月營收(千元)']=current_revenue
        revenue_dict['最近一季平均月營收(千元)']=average_revenue_last_season
        final_revenue_list.append(revenue_dict)
    def append_eps(stock,current_eps,average_eps_last_season):
        eps_dict={}
        eps_dict['股票']=stock
        eps_dict['最近一月盈餘(元)']=current_eps
        eps_dict['最近一季平均月盈餘(元)']=average_eps_last_season
        final_eps_list.append(eps_dict)
    next_month = 0
    while True:
        time.sleep(5) 
        # 獲取當前日期
        today = datetime.date.today()
        # 獲取年月日
        year = str(today.year-1911)
        month = str(today.month)
        day = str(today.day)
        print(f'month : {month}, date : {day}')
        # month = '2'
        # day = '20'
        #到下一個月就重置list
        if month == next_month:
            past_stock_number=[]
        next_month = str(today.month+1)
        
        #設置driver
        #driver = webdriver.Edge(executable_path='C:\\Program Files(x86)\\Microsoft\\Edge\\Application\\msedge')
        service = Service(EdgeChromiumDriverManager().install())
        options = Options()
        options.add_argument("--headless") # or use pyvirtualdiplay
        options.add_argument("--no-sandbox") # needed, because colab runs as root
        options.headless = True
        inconnect = True
        while inconnect:
            try:
                driver = webdriver.Chrome(service=service, options=options)
                url = "https://mops.twse.com.tw/mops/#/web/t05st02"
                time.sleep(2)
                driver.get(url)
                inconnect = False
            except:
                inconnect = True # 直到連接上為止

        #特定的年月日
        time.sleep(1)
        # 年份輸入框
        year_box = driver.find_element(By.XPATH, "/html/body/div/div/div/section/div[2]/div[1]/div[2]/div/div/div[1]/input")
        year_box.send_keys(year)

        # 月份下拉選單
        month_dropdown = driver.find_element(By.XPATH, "/html/body/div/div/div/section/div[2]/div[1]/div[2]/div/div/div[2]/select")
        dropdown_month = Select(month_dropdown)
        dropdown_month.select_by_visible_text(f'{month}月')

        # 日期下拉選單
        day_dropdown = driver.find_element(By.XPATH, "/html/body/div/div/div/section/div[2]/div[1]/div[2]/div/div/div[3]/select")
        dropdown_day = Select(day_dropdown)
        dropdown_day.select_by_visible_text(day)
        day_dropdown.send_keys(Keys.ENTER)
        
        button = driver.find_element(By.ID, "searchBtn")
        button.click()
        
        # year_box = driver.find_element(By.ID,'year')
        # year_box.send_keys(year)
        # month_dropdown = driver.find_element(By.ID,'month')
        # dropdown_month = Select(month_dropdown)
        # dropdown_month.select_by_visible_text(month)
        # day_dropdown = driver.find_element(By.ID,'day')
        # dropdown_day = Select(day_dropdown)
        # dropdown_day.select_by_visible_text(day)s
        # day_dropdown.send_keys(Keys.ENTER)
        
        time.sleep(2)
        soup = BeautifulSoup(driver.page_source,"html.parser")     
        # 選擇 table>tbody>tr 元素
        tr_elements = soup.select("table > tbody > tr")

        # 或者
        tr_elements = soup.find("table").find("tbody").find_all("tr")
        tr_withkeyword=[]
        tr_indixes = []

        # 找尋新聞的 keyword
        keywords = [
            "達公布注意交易資訊", "達公佈注意交易資訊", "注意交易資訊標準",
            "達公布注意資訊標準", "達公佈注意資訊標準", "達公布交易資訊標準",  
            "達公布注意交易資訊標準", "達公佈注意交易資訊標準", 
            "近期股價異常，故公告相關訊息", "集中交易市場有異常交易情形",
            "要求公布相關資訊","要求公告相關訊息"
        ]
        default_keywoed = "發言日期"
        # 每個keyword中可能包含不規則空格
        regex_keywords = ['\\s*'.join(re.escape(char) for char in kw) for kw in keywords]
        regex_pattern = '|'.join(regex_keywords)
        compiled_pattern = re.compile(regex_pattern)
        default_pattern = re.compile(default_keywoed)

        # 檢查 <td> 元素
        i = 1
        for tr in tr_elements:
            td_elements = tr.find_all('td')
            for td in td_elements:
                if default_pattern.search(td.text):
                    i -= 1
                    break            
                if compiled_pattern.search(td.text):
                    tr_withkeyword.append(tr)
                    tr_indixes.append(str(i))
            i += 1

        if not tr_withkeyword:
            print('今天無警示股')
    
        def get_detail_info(tr_withkeyword, tr_indexes, driver):
            all_data = []
            
            for index, tr_element in zip(tr_indexes, tr_withkeyword):
                try:
                    # 獲取識別信息
                    company_code = tr_element.find('td', {'data-title': '公司代號:'}).find('span').text.strip()
                    company_name = tr_element.find('td', {'data-title': '公司名稱:'}).find('span').text.strip()
                    date = tr_element.find('td', {'data-title': '發言日期:'}).find('span').text.strip()
                    time_info = tr_element.find('td', {'data-title': '發言時間:'}).find('span').text.strip()
                    subject = tr_element.find('td', {'data-title': '主旨:'}).find('span').text.strip()
                    
                    print(f"正在處理: {company_code} {date}")
                    
                    original_window = driver.current_window_handle # 紀錄初始 window
                    
                    # 找到並點擊按鈕
                    wait = WebDriverWait(driver, 10)
                      # 找到所有按鈕
                    button = driver.find_element(By.XPATH, 
                        f'/html/body/div/div/div/section/div[3]/div/div/div[2]/div[2]/div/table/tbody/tr[{index}]/td[6]/span/button')
                    button.click()
                            
                    time.sleep(2) 
                    
                    # 獲取所有窗口句柄
                    handles = driver.window_handles

                    # 切換到新開啟的窗口
                    for handle in handles:
                        if handle != original_window:
                            driver.switch_to.window(handle)
                            break
                        
                    html_content = driver.page_source
                    soup = BeautifulSoup(html_content, 'html.parser')

                    # 獲取所有 td 元素
                    tds = soup.select("table tr td")

                    # 找出最長的內容
                    max_length = 0
                    longest_text = ""

                    for td in tds:
                        # 獲取每行的 td 元素
                        try:
                            text = td.text
                            if len(text) > max_length:
                                max_length = len(text)
                                longest_text = text
                        except:
                            continue

                    # 抓取新頁面的詳細資訊
                    detail_data = {
                        'company_code': company_code,
                        'company_name': company_name,
                        'date': date,
                        'time': time_info,
                        'subject': subject,
                        'content': longest_text
                    }
                    
                    all_data.append(detail_data)
                    
                    # 返回 original window
                    driver.switch_to.window(original_window)
                    
                    time.sleep(1)  # 給予頁面返回時間
                    
                except Exception as e:
                    print(f"處理 {company_code} {date} 時發生錯誤: {e}")
                    try:
                        driver.back()  # 發生錯誤時嘗試返回上一頁
                        time.sleep(1)
                    except:
                        pass
                    continue
            
            return all_data
            
        # 獲取詳細資訊
        results = get_detail_info(tr_withkeyword, tr_indixes, driver)
        
        # # 印出結果
        # for result in results:
        #     print("\n公司代號:", result['company_code'])
        #     print("日期:", result['date'])
        #     print("時間:", result['time'])
        #     print("主旨:", result['subject'])
        #     print("詳細內容:", result['content'][:200] + "...")  # 只印出前200字
    
        def convert_eps(uncleaned_eps):
            cleaned_eps=''
            minus_flag=False
            for char in uncleaned_eps:
                if char=="(" or char==')':
                    minus_flag=True
                    continue
                else:
                    cleaned_eps+=char
            if minus_flag:
                return str(-float(cleaned_eps))
            else:
                return cleaned_eps
            
        # 警示股股票代號和股票名稱
        stock_number=[]
        stock_name=[]
        stock_list=[]
        eps_list=[]
        
        # parse the content of result
        for result in results:
            target_value = result['content']         
            try:
                eps_target = re.search(r"每股盈餘(?:\s+)?(?:\(虧損\)|（虧損）)?(?:\(損\)|（損）)?(?:\(虧\)|（虧）)?(?:\s+)?(?:\(元\)|（元）)?(?:\s+)?(?:\(單位：分美元\)|（單位：分美元）)?(?:\s+)?(\()?(-?[\d.]+)(\))?", target_value) #可能還會有格式的例外
                eps_target = f"{eps_target.group(1) if eps_target.group(1) else ''}{eps_target.group(2)}{eps_target.group(3) if eps_target.group(3) else ''}"
                eps_target = convert_eps(eps_target)
                eps_list.append(eps_target)
            except:
                eps_target = 'none'
            if eps_target != 'none':
                td_elements=soup.find_all('td')
                stock_number.append(result['company_code'])
                stock_name.append(result['company_name'])
                stock_list.append(result['company_code']+result['company_name'])
                print(result['company_code']+result['company_name'])
                
        #把重複過的股票排除
        for i in range(len(stock_number)):
            if stock_number[i] in past_stock_number:
                stock_number[i]=''
                stock_name[i]=''
                stock_list[i]=''
                eps_list[i]=''
        #創建營收和盈餘的list
        final_revenue_list=[]
        final_eps_list=[]

        for stock_number,stock,eps_ in zip(stock_number,stock_list,eps_list):
            if stock_number=='':
                continue
            past_stock_number.append(stock_number)
            try:
                try:
                    url = "https://tw.stock.yahoo.com/quote/"+stock_number+".TW/eps"
                    driver.get(url)
                    time.sleep(1) 
                    find_past_eps=driver.find_element(By.XPATH,'//*[@id="qsp-eps-table"]/div/div[2]/div/div/ul/li[1]/div/div[2]/span')
                    stock_past_eps=find_past_eps.text
                    average_stock_past_eps=round(float(stock_past_eps)/3,2)
                    if eps_ != 'none':
                        append_eps(stock,eps_,str(average_stock_past_eps))
                    else:
                        append_eps(stock,'none',str(average_stock_past_eps))
                except:
                    url = "https://tw.stock.yahoo.com/quote/"+stock_number+".TWO/eps"
                    driver.get(url)
                    time.sleep(1)
                    find_past_eps=driver.find_element(By.XPATH,'//*[@id="qsp-eps-table"]/div/div[2]/div/div/ul/li[1]/div/div[2]/span')
                    stock_past_eps=find_past_eps.text
                    average_stock_past_eps=round(float(stock_past_eps)/3,2)
                    if eps_ != 'none':
                        append_eps(stock,eps_,str(average_stock_past_eps))
                    else:
                        append_eps(stock,'none',str(average_stock_past_eps))
            except NoSuchElementException:
                append_eps(stock,eps_,'none')
            try:
                try:
                    url = "https://tw.stock.yahoo.com/quote/"+stock_number+".TW/revenue"
                    driver.get(url)
                    time.sleep(1)
                    find_revenue=driver.find_element(By.XPATH,'//*[@id="qsp-revenue-table"]/div/div[2]/div/div/ul/li[1]/div/div[2]/ul/li[1]/span')
                    stock_current_revenue=find_revenue.text
                    season_button=driver.find_element(By.XPATH,'//*[@id="qsp-revenue-chart"]/div[2]/div/div[2]/button/span')
                    driver.execute_script("arguments[0].click();", season_button)
                    time.sleep(1)
                    find_past_revenue=driver.find_element(By.XPATH,'//*[@id="qsp-revenue-table"]/div/div[2]/div/div/ul/li[1]/div/div[2]/ul/li[1]/span')
                    stock_past_revenue=find_past_revenue.text
                    stock_past_revenue = stock_past_revenue.replace(',', '')
                    average_stock_past_revenue=round(int(stock_past_revenue)/3,2)
                    append_revenue(stock,stock_current_revenue,str(average_stock_past_revenue))
                except:
                    url = "https://tw.stock.yahoo.com/quote/"+stock_number+".TWO/revenue"
                    driver.get(url)
                    time.sleep(1) 
                    find_revenue=driver.find_element(By.XPATH,'//*[@id="qsp-revenue-table"]/div/div[2]/div/div/ul/li[1]/div/div[2]/ul/li[1]/span')
                    stock_current_revenue=find_revenue.text
                    season_button=driver.find_element(By.XPATH,'//*[@id="qsp-revenue-chart"]/div[2]/div/div[2]/button/span')
                    driver.execute_script("arguments[0].click();", season_button)
                    time.sleep(1)
                    find_past_revenue=driver.find_element(By.XPATH,'//*[@id="qsp-revenue-table"]/div/div[2]/div/div/ul/li[1]/div/div[2]/ul/li[1]/span')
                    stock_past_revenue=find_past_revenue.text
                    stock_past_revenue = stock_past_revenue.replace(',', '')
                    average_stock_past_revenue=round(int(stock_past_revenue)/3,2)
                    append_revenue(stock,stock_current_revenue,str(average_stock_past_revenue))
            except NoSuchElementException:
                append_revenue(stock,'none','none')

        if final_revenue_list and final_eps_list:
            print(final_revenue_list)
            print(final_eps_list)
            driver.quit()
        
    
        for revenue,eps in zip(final_revenue_list,final_eps_list):
            try:
                revenue_grow_up_percentage = 0
                eps_grow_up_percentage = 0
                if revenue['最近一月營收(千元)'] != 'none' and revenue['最近一季平均月營收(千元)'] != 'none' and eps['最近一月盈餘(元)'] != 'none' and eps['最近一季平均月盈餘(元)'] != 'none':
                    if float(revenue['最近一季平均月營收(千元)']) != 0:
                        revenue_grow_up_percentage=(float(revenue['最近一月營收(千元)'].replace(',', ''))-float(revenue['最近一季平均月營收(千元)']))/abs(float(revenue['最近一季平均月營收(千元)']))*100
                    if float(eps['最近一季平均月盈餘(元)']) != 0:
                        eps_grow_up_percentage=(float(eps['最近一月盈餘(元)'])-float(eps['最近一季平均月盈餘(元)']))/abs(float(eps['最近一季平均月盈餘(元)']))*100
                revenue_grow_up_percentage_str = "{:.2f}".format(revenue_grow_up_percentage)
                eps_grow_up_percentage_str = "{:.2f}".format(eps_grow_up_percentage)
                message=revenue['股票']+"\n最近一月營收(千元):"+revenue['最近一月營收(千元)'].replace(',', '')+"\n最近一季平均月營收(千元):"+revenue['最近一季平均月營收(千元)']+"\n成長:"+revenue_grow_up_percentage_str+"%"+"\n最近一月盈餘(元):"+eps['最近一月盈餘(元)']+"\n最近一季平均月盈餘(元):"+eps['最近一季平均月盈餘(元)']+"\n成長:"+eps_grow_up_percentage_str+"%"
                bot.send_message(CHAT_ID,message)
            except Exception as e:
                print(f"sending message error : {e}")
                continue
        
        retry_count = 0  # restart the number
            
    return past_stock_number
 
if __name__ == "__main__":
    next_month='0'
    past_stock_number = []
    
    retry_limit = 5

    while retry_count < retry_limit:
        try:
            past_stock_number = main(past_stock_number)
            retry_count = 0 
        except Exception as e:
            print(f"發生錯誤: {e}, 正在嘗試第 {retry_count + 1} 次重試...")
            time.sleep(1) 
            retry_count += 1

    if retry_count == retry_limit:
        print("重試次數達到上限，程序終止。")