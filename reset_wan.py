import time
import mysql.connector
import asyncio
import random
import re
import datetime
from paramiko import SSHClient
from paramiko import AutoAddPolicy

t1 = time.time()

django_db = mysql.connector.connect(host="172.18.0.2",user="root",password="benz4466",database="django_db")
query_db = django_db.cursor()

db_cacti = mysql.connector.connect(host="10.1.0.50",user="admin",password="1qaz2wsx",database="automation")
exec_command = db_cacti.cursor()


ip_list = ['www.google.com','8.8.8.8','8.8.4.4']

url = 'https://notify-api.line.me/api/notify'
token = 'xoQZ0Qaq5e0lf4eFraNNs7bOVwOioE9YyNNq8zqBLjw' #<-- Token line
headers = {'content-type':'application/x-www-form-urlencoded','Authorization':'Bearer '+token}

timestr = datetime.datetime.now()
date = timestr.strftime("%d-%m-%Y")
time_now = timestr.strftime("%X")
time_stamp = date + ' ' + time_now

def fetch_db():
    query_db.execute(f"select * from still_problem where status='000';")
    id_list = []
    ip_list = []
    status_list = []
    for firsh_fetch in query_db:
        get_id = firsh_fetch[0]
        get_ip = firsh_fetch[1]
        get_status = firsh_fetch[4]
        id_list.append(get_id)
        ip_list.append(get_ip)
        status_list.append(get_status)
    return id_list,ip_list,status_list

async def select_db(_get):
    query_db.execute(f"select * from still_problem where ip = '{_get}' and status = '000';")
    id_list = []
    ip_list = []
    status_list = []
    for firsh_fetch in query_db:
        get_id = firsh_fetch[0]
        get_ip = firsh_fetch[1]
        get_status = firsh_fetch[4]
        id_list.append(get_id)
        ip_list.append(get_ip)
        status_list.append(get_status)
    return id_list,ip_list,status_list

async def get_host(_get):
    exec_command.execute(f"select * from automation_ros_host where status = 001 and host_ros = '{_get}';")
    id_list = []
    ip_list = []
    for firsh_fetch in exec_command:
        get_id = firsh_fetch[1]
        get_ip = firsh_fetch[2]
        id_list.append(get_id)
        ip_list.append(get_ip)
    return id_list,ip_list

async def get_host_cacti(_get):
    query_db.execute(f"select * from automation where status = 001 and host_ros = '{_get}';")
    id_list = []
    ip_list = []
    for firsh_fetch in query_db:
        get_id = firsh_fetch[1]
        get_ip = firsh_fetch[2]
        id_list.append(get_id)
        ip_list.append(get_ip)
    return id_list,ip_list

async def update_db(_get):
    query_db.execute(f"update still_problem set status = '001' where id = '{_get}'")
    django_db.commit()

async def insert_db(_get):
    #query_db.execute(f"insert into finish_log (ip,datetime) values ('{_get}',now());")
    exec_command.execute(f"insert into line_notify (display,host_ip,code,update_time) values ('ROS','{_get}','Fix Already',now());")
    db_cacti.commit()

async def insert_cacti2(_get):
    exec_command.execute(f"insert into line_notify (ip,datetime) values ('{_get}',now());")
    db_cacti.commit()

async def enable_host(_get):
    exec_command.execute(f"update automation_ros_host set status = '000' where host_ros = '{_get}';")
    db_cacti.commit()

async def sshros(_get):
    try:
        client = SSHClient()
        client.set_missing_host_key_policy(AutoAddPolicy())
        client.connect(_get, port=22,username='admin',password='1qaz2wsx',timeout=0.2)
        stdin,stdout,stderr = client.exec_command(f"ping count=5 {random.choice(ip_list)} interval=200ms")
        await asyncio.sleep(0.5)
        client.close()
        for output_from_stdout in stdout:
            output_from_stdout.strip()
        output_ = output_from_stdout
        output_check = r"(ms)"
        if re.search(output_check, output_):
            result = '1'
        else:
            result = '2'
    except:
        return '9'
    return result

async def reset_wan(host):
    off = await asyncio.create_subprocess_shell(f"snmpset -c htvnms -v 2c {host} 1.3.6.1.4.1.14988.1.1.8.1.1.3.1 s 1")
    await asyncio.sleep(5)
    on = await asyncio.create_subprocess_shell(f"snmpset -c htvnms -v 2c {host} 1.3.6.1.4.1.14988.1.1.8.1.1.3.2 s 1")
    await asyncio.sleep(5)
    await off.wait()
    await on.wait()
    if off.returncode == 0 and on.returncode == 0:
        #commit = await asyncio.create_subprocess_shell("python /home/benz/python_engineer/project1/mikrotik/ssh_mikrotik.py " + host)## <-- python file for ssh mikrotik to check Internet
        #await commit.wait()
        result_s = await sshros(host)
    else:
        pass
    return result_s,host

async def ping(host):
    ping_process = await asyncio.create_subprocess_shell("ping -c 1 " + host + " > /dev/null 2>&1")
    await ping_process.wait()

    if ping_process.returncode == 0:
        print(host + " | Online")
        result_ = await reset_wan(host)
        print(result_)
        if result_[0] == '1':
            select_ = await asyncio.create_task(select_db(host))
            for id_,ip_ in zip(select_[0],select_[1]): 0
            await asyncio.sleep(0.1)
            await asyncio.create_task(update_db(id_))
            await asyncio.sleep(0.1)
            await asyncio.create_task(insert_db(ip_))
            select_host = await asyncio.create_task(get_host(host))
            for id_,ip_ in zip(select_host[0],select_host[1]): 0
            await asyncio.sleep(0.1)
            await asyncio.create_task(enable_host(ip_))
            await asyncio.sleep(0.1)
        elif result_[0] == '2':
            pass
        else:
            pass       
    else:
        print(host + " | Not Online")
    return 

async def ping_all(_get):
    tasks = []
    for i in _get:
        tasks.append(asyncio.create_task(ping(i)))
    await asyncio.gather(*tasks, return_exceptions = True)

if __name__ == '__main__':
    keep = fetch_db()
    result0 = keep[0]
    result1 = keep[1]
    result2 = keep[2]
    asyncio.run(ping_all(result1))
    t2 = time.time() - t1
    print(f"{t2:0.2f} {time_stamp}")
    django_db.close()
    db_cacti.close()