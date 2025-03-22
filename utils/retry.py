from time import sleep
from utils.config import config
from urllib.parse import urlparse  # 添加导入

if config.open_driver:
    try:
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.common.exceptions import TimeoutException
    except:
        pass

max_retries = 2


def retry_func(func, retries=max_retries, name=""):
    """
    Retry the function
    """
    host = urlparse(name).hostname if name else name
    for i in range(retries):
        try:
            sleep(1)
            return func()
        except Exception as e:
            if name and i < retries - 1:
                print(f"Failed to connect to the {host}. Retrying {i+1}...")
            elif i == retries - 1:
                raise Exception(
                    f"Failed to connect to the {host} reached the maximum retries."
                )
    raise Exception(f"Failed to connect to the {host} reached the maximum retries.")


def locate_element_with_retry(
    driver, locator, timeout=config.request_timeout, retries=max_retries
):
    """
    Locate the element with retry
    """
    wait = WebDriverWait(driver, timeout)
    for _ in range(retries):
        try:
            return wait.until(EC.presence_of_element_located(locator))
        except TimeoutException:
            driver.refresh()
    return None


def find_clickable_element_with_retry(
    driver, locator, timeout=config.request_timeout, retries=max_retries
):
    """
    Find the clickable element with retry
    """
    wait = WebDriverWait(driver, timeout)
    for _ in range(retries):
        try:
            return wait.until(EC.element_to_be_clickable(locator))
        except TimeoutException:
            driver.refresh()
    return None
