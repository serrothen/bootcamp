#!/usr/bin/env python3

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException 
#,ElementClickInterceptedException,NoSuchElementException
import os

def get_credentials():
    """Get login credentials from environment variables.."""

    user_name = os.getenv('CHECK_LOGIN_USR')
    user_passwd = os.getenv('CHECK_LOGIN_PWD')

    return user_name,user_passwd


def setup_browser():
    """Setup browser."""

    browser = webdriver.Firefox()
    wait = WebDriverWait(browser, 10)

    return browser,wait


def login_forum(browser,wait,user_name,user_passwd):
    """Cascade of logins."""

    element = browser.find_element(By.XPATH, \
                           "//*[contains(@href,'login')]")
    element.click()

    # SAML login
    element = wait.until(
    EC.element_to_be_clickable((By.XPATH, \
                     "//*[contains(@href,'/auth/saml2')]"))
    )
    element.click()
    
    # MS login
    element = wait.until(
    EC.presence_of_element_located((By.XPATH, \
                           "//input[@type='email']"))
    )
    element.click()
    element.clear()
    element.send_keys(user_name)
    element = wait.until(
    EC.element_to_be_clickable((By.XPATH, \
                     "//input[@value='Next']"))
    )
    element.click()
    
    # BP login
    element = wait.until(
    EC.presence_of_element_located((By.XPATH, \
                           "//input[@id='passwordInput']"))
    )
    element.click()
    element.clear()
    element.send_keys(user_passwd)
    element = wait.until(
    EC.element_to_be_clickable((By.XPATH, \
                     "//*[@id='submitButton']"))
    )
    element.click()
    
    # Stay signed in?
    element = wait.until(
    EC.element_to_be_clickable((By.XPATH, \
                     "//input[@value='No']"))
    )
    element.click()

    return browser


def text_analysis(browser,wait,forum_text):
    """Perform the text analysis."""

    # split text into list of words
    word_list = forum_text.split()
    
    ## find quotes for important, i.e. capitalized words 
    ## (attempt failed since popup could not be closed)
    #important_words = [word.strip(".") for word in word_list \
    #                   if word==word.capitalize()]
    #
    #quotes = []
    #for word in important_words:
    #
    #    browser.get("https://www.zitate.de/")
    #
    #    # popup
    #    element = wait.until(
    #    EC.presence_of_element_located((By.XPATH, \
    #                   "//button[contains(text(),'Alles akzeptieren')]"))
    #    )
    #    element.click()
    #
    #    try:
    #
    #        element = wait.until(
    #        EC.presence_of_element_located((By.XPATH, \
    #                       "//input[@placeholder='suchen']"))
    #        )
    #        element.click()
    #        element.clear()
    #        element.send_keys(word)
    #    
    #        element = wait.until(
    #        EC.element_to_be_clickable((By.XPATH,"//*[@id='okbuttonpress']"))
    #        )
    #        element.click()
    #
    #        element = wait.until(
    #        EC.presence_of_element_located((By.XPATH, \
    #                       "//*[@class='well quote-box'][0]"))
    #        )
    #        quotes.append(element.text)
    #        print(quotes)
    #    except (TimeoutException,ElementClickInterceptedException):
    #        # popup
    #        try:
    #            element = browser.find_element(By.XPATH, \
    #                                   "//button[class='floatclose']")
    #        except NoSuchElementException:
    #            browser.switch_to.frame(element)
    #            element = browser.find_element(By.XPATH, \
    #                                   "//button[class='floatclose']")
    #            element.click()
    
    # unique words
    unique_words = set(map(str.lower,word_list))
    
    ratio = f"Bruchteil einmalig vorkommender Wörter:\n"+ \
             "{len(unique_words)}/{len(word_list)}"
    
    # special word
    special_word = "und"
    special_length = len(special_word)
    special_number = len([word for word in word_list \
                          if word==special_word])
    
    # histogram of word-lengths
    lengths = [len(word) for word in word_list]
    # count lengths
    dct = {length:0 for length in range(max(lengths)+1)}
    
    for length in lengths:
        dct[length] += 1
    # sort lengths
    lengths_sort = list(dct.keys())
    lengths_sort.sort()
    output_lst = ["Histogramm der Wortlängen. "+ \
                  "Das Wort \"und\" ist durch * markiert:"]
    # histogram
    for length in lengths_sort:
        if (length==special_length):
            output_lst.append(str(length).zfill(2) \
                             +" | "+"*"*special_number \
                             +"#"*dct[length])
        else:
            output_lst.append(str(length).zfill(2) \
                             +" | "+"#"*dct[length])
    
    analysis = ratio+"\n\n"+"\n".join(output_lst)

    return analysis


def submit_analysis(browser,wait,forum_url,analysis):
    """Write analysis to forum."""

    # overcome problems with expandable elements
    expanded = False
    while (not expanded):
    
        try:
            browser.get(forum_url)
            expanded = True
    
            element = wait.until(
            EC.element_to_be_clickable((By.XPATH, \
                             "//*[contains(text(),'Neues Thema hinzufügen')]"))
            )
            element.click()
    
            element = wait.until(
            EC.element_to_be_clickable((By.XPATH, \
                             "//input[@value='Erweitert']"))
            )
        except TimeoutException:
            expanded = False
    
    element.click()
    
    
    # handle insecure connection (not necessary)
    #current_url = browser.current_url
    #browser.get(current_url)
    #
    #element = wait.until(
    #EC.element_to_be_clickable((By.XPATH, \
    #                 "//button[@id='advancedButton']"))
    #)
    ##element.send_keys(Keys.RETURN)
    #element.click()
    #
    #element = wait.until(
    #EC.element_to_be_clickable((By.XPATH, \
    #                 "//button[contains(text(),'Accept the Risk and Continue')]"))
    #)
    ##element.send_keys(Keys.RETURN)
    #element.click()
    #
    #print("before Resend")
    #element = wait.until(
    #EC.element_to_be_clickable((By.XPATH, \
    #                 "//button[contains(text(),'Resend')]"))
    #)
    #print("after Resend")
    ##element.send_keys(Keys.RETURN)
    #element.click()
    
    
    # enter subject
    element = wait.until(
    EC.presence_of_element_located((By.XPATH, \
                           "//input[@name='subject']"))
    )
    element.click()
    element.clear()
    element.send_keys("Textanalyse?")
    
    # enter textblock
    element = wait.until(
    EC.presence_of_element_located((By.XPATH, \
                           "//*[@role='textbox']"))
    )
    element.click()
    element.clear()
    element.send_keys(analysis)
    
    
    # add Tags
    # enter Selenium
    element = wait.until(
    EC.presence_of_element_located((By.XPATH, \
                   "//input[starts-with(@placeholder,'Tags')]"))
    )
    element.click()
    element.clear()
    element.send_keys("Selenium,")
    # click somewhere else
    element = browser.find_element(By.XPATH, \
                           "//input[@name='subject']")
    element.click()
    
    # enter Python
    element = wait.until(
    EC.presence_of_element_located((By.XPATH, \
                           "//input[starts-with(@placeholder,'Tags')]"))
    )
    element.click()
    element.clear()
    element.send_keys("Python,")
    # click somewhere else
    element = browser.find_element(By.XPATH, \
                           "//input[@name='subject']")
    element.click()
    
    # enter Text
    element = wait.until(
    EC.presence_of_element_located((By.XPATH, \
                           "//input[starts-with(@placeholder,'Tags')]"))
    )
    element.click()
    element.clear()
    element.send_keys("Text,")
    # click somewhere else
    element = browser.find_element(By.XPATH, \
                           "//input[@name='subject']")
    element.click()
    
    # enter Analyse
    element = wait.until(
    EC.presence_of_element_located((By.XPATH, \
                           "//input[starts-with(@placeholder,'Tags')]"))
    )
    element.click()
    element.clear()
    element.send_keys("Analyse,")
    # click somewhere else
    element = browser.find_element(By.XPATH, \
                           "//input[@name='subject']")
    element.click()

    # submit contribution
    element = wait.until(
    EC.presence_of_element_located((By.XPATH, \
                           "//input[@name='submitbutton']"))
    )
    element.click()


def main():
    """Login to forum, read text, analyze it and submit the analysis."""

    user_name, user_passwd = get_credentials()
    
    browser,wait = setup_browser()
    
    browser.get("https://learnhub.bearingpoint.com/mod/forum/view.php?id=1808")
    
    browser = login_forum(browser,wait,user_name,user_passwd)
    
    # forum text
    element = wait.until(
    EC.presence_of_element_located((By.XPATH, \
                           "//*[@id='intro']"))
    )
    forum_text = element.text
    forum_url = browser.current_url
    
    analysis = text_analysis(browser,wait,forum_text)
    
    submit_analysis(browser,wait,forum_url,analysis)
    
    browser.close()


if (__name__ == "__main__"):
    main()
