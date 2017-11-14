#! /usr/bin/python
# -*- coding: utf-8 -*-
import itchat
import time
import re
import os


def get_msg_info(msg,setting):
    '''获取消息内容并解析'''

    myid = itchat.get_friends()[0]['UserName']  # 本人ID
    response = None #初始化回复内容
    msg_rev_time = time.time() #接收消息的时间戳
    msg_rev_time_format = time.strftime('%Y-%m-%d %H:%M:%S',time.localtime()) #格式化接收时间
    msg_type = msg['Type'] #文件类型
    msg_id = msg['MsgId'] #消息ID
    msg_time = msg['CreateTime'] #消息时间戳
    msg_content = None #发送内容
    msg_filename = None #附件的名字
    msg_url = None #分享的链接
    group_name = None #群聊名称
    msg_user_remarkname = None
    #如果为群聊消息
    msg_from = msg['ActualUserName'] if msg.get('ActualUserName') else msg['FromUserName'] # 发送者ID
    msg_to = msg['ToUserName'] if msg_from == myid else None #接受者ID
    if msg_to <> 'filehelper':
        msg_user_nickname = msg['ActualNickName'] if msg.get('ActualNickName') else msg['User']['NickName'] # 发送者昵称
        msg_user_remarkname = itchat.search_friends(userName=msg_from)['RemarkName'] if itchat.search_friends(userName=msg_from) else msg_user_remarkname #发送者备注
        group_name = msg['User']['NickName'] if msg['User']['NickName'] and msg.get('ActualNickName') else group_name #群聊名称



    #判断消息类型并处理
    _judge_msg_type(msg, msg_type)
    #初始化个人自动回复状态
    _get_user_auto(setting, msg_from)

    if msg_type == 'Text' or msg_type == 'Friends':
        msg_content = msg['Content']

    # 如果发送为图片、视频、语音、附件
    elif msg_type == 'Picture' or msg_type == 'Video' \
            or msg_type == 'Recording' or msg_type == 'Attachment':
        msg_filename = msg['FileName']


    # 如果发送为名片推荐
    elif msg_type == 'Card':
        msg_content = '"'+msg['RecommendInfo']['NickName']+'"' + u'的名片，性别为：'
        if msg['RecommendInfo']['Sex'] == 1:
            msg_content += u'男'
        else:
            msg_content += u'女'

    # 如果发送为地图定位
    elif msg_type == 'Map':
        x, y, location = re.search(
            "<location x=\"(.*?)\" y=\"(.*?)\".*label=\"(.*?)\".*", msg['OriContent']).group(1, 2, 3)
        msg_content = u'地址：%s\n经度：%s，纬度：%s' % (location, x, y)

    # 如果发送为分享
    elif msg_type == 'Sharing':
        msg_content = msg['Text']
        msg_url = msg['Url']

    # 其他消息类型
    else:
        pass


    #对相应的消息作回复
    # 如果为我本人发送并发送给自己
    if msg_from == myid and msg_to == 'filehelper':
        if msg_content == u'帮助':
            response = u'[00]->手动清理缓存的超时信息' \
                       u'\n\n[01]->开启自动回复\n\n[02]->关闭自动回复' \
                       u'\n\n[03]->防止撤销操作\n\n[04]->允许撤销操作' \
                       u'\n\n[05]->机器人自动陪聊\n\n[06]->关闭机器人陪聊' \
                       u'\n\n[07]->清除缓存照片\n\n[08]->清除缓存视频' \
                       u'\n\n[09]->清除缓存附件\n\n[10]->清除缓存音频'
        elif msg_content == u'01':
            setting.auto_replay = True
            for k,v in setting.person_auto.items():
                setting.person_auto[k] = True
            response = u'自动回复已开启！'
        elif msg_content == u'02':
            setting.auto_replay = False
            setting.person_auto.clear()
            response = u'自动回复已关闭！'
        elif msg_content == u'03':
            setting.revocation = True
            response = u'防撤销功能已开启！'
        elif msg_content == u'04':
            setting.revocation = False
            response = u'防撤销功能已关闭！'
        elif msg_content == u'07':
            pic_count = _clear_file('Picture')
            response = u'正在手动清理本地图片...\n\n共清理图片文件个数：%s' % pic_count
        elif msg_content == u'08':
            vid_count = _clear_file('Video')
            response = u'正在手动清理本地视频...\n\n共清理视频文件个数：%s' % vid_count
        elif msg_content == u'09':
            vid_count = _clear_file('Attachment')
            response = u'正在手动清理本地附件...\n\n共清理附件文件个数：%s' % vid_count
        elif msg_content == u'10':
            vid_count = _clear_file('Recording')
            response = u'正在手动清理本地音频...\n\n共清理音频文件个数：%s' % vid_count
        elif msg_content == u'00':
            before_count = len(setting.msg_information)
            now_count = len(_check_msg_time(setting.msg_information))
            response = u'正在手动清理超时的信息！\n\n清理前会话数：%s \n清理后会话数：%s' % (before_count, now_count)
        else:
            response = u'请输入正确的指令'

    elif msg_from <> myid:
        if setting.person_auto[msg_from] == True and group_name == None :
            response = u'[自动回复]您好，我现在有事不在，一会再和您联系。\n\n如需关闭自动提醒，请回复数字[0]'
            if msg_content == '0':
                setting.person_auto[msg_from] = False
                response = u'您已关闭自动回复，我一会再和您联系！'

        if setting.revocation == True:
            #先清理过期数据
            now_time = time.time()
            for k,v in setting.msg_information.items():
                time_difference = int(now_time) - int(v['msg_time'])
                if time_difference >= 2*60+10:  # 如果时间大于2min,10秒缓冲期
                    setting.msg_information.pop(k)
            setting.msg_information.update(
                {
                    msg_id: {
                        'msg_rev_time': msg_rev_time, 'msg_rev_time_format': msg_rev_time_format,
                        'msg_type': msg_type, 'msg_from': msg_from, 'msg_id': msg_id, 'msg_time': msg_time,
                        'msg_content': msg_content, 'msg_filename': msg_filename, 'msg_url': msg_url,
                        'msg_user_nickname': msg_user_nickname, 'msg_user_remarkname': msg_user_remarkname,
                        'group_name':group_name
                    }

                }
            )
            if msg_type == 'Picture' or msg_type == 'Video' or msg_type == 'Recording' or msg_type == 'Attachment':
                msg['Text']('./' + msg_type + '/' + msg_filename)  # 下载文件到相应的文件夹中

    if msg_to == 'filehelper' and msg_from == myid:
        itchat.send(response, toUserName='filehelper')
    else:
        itchat.send(response, toUserName=msg_from)


def _judge_msg_type(msg,msg_type):
    '''判断消息类型并处理'''
    # 如果发送为纯文本或好友推荐




def _get_user_auto(setting,msg_from):
    '''初始化个人自动回复状态'''
    if setting.person_auto.get(msg_from) <> None:
        setting.person_auto[msg_from] = setting.person_auto.get(msg_from)
    else:
        setting.person_auto.update({msg_from:setting.auto_replay})



def _clear_file(filetype):
    '''清理本地文件'''
    addr = './' + filetype + '/'
    file_list = os.listdir(addr)
    # file_list = os.listdir(addr)[1:]
    file_count = len(file_list)
    for i in file_list:
        os.remove(addr + i)
    return file_count



def _check_msg_time(dict):
    '''清除时间超过2min的消息，节省内存'''
    now_time = time.time()
    if dict:
        for k, v in dict.items():
            time_difference = int(now_time) - int(v['msgtime'])
            if time_difference >= 2 * 60 + 10: # 如果时间大于2min,10秒缓冲期
                dict.pop(k)
    return dict



def send_revocation(msg,setting):
    '''发送被撤回的信息'''
    revocation_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(msg['CreateTime']))
    revocation_msg_id = re.search("\<msgid\>(.*?)\<\/msgid\>", msg['Content']).group(1)  # 在返回的content查找撤回的消息的id
    revocation_msg = setting.msg_information[revocation_msg_id]
    revocation_type = revocation_msg['msg_type']
    revocation_remarkname = revocation_msg['msg_user_remarkname']
    revocation_nickname = revocation_msg['msg_user_nickname']
    isgroup = revocation_msg['group_name']
    revocation_msg_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(revocation_msg['msg_time']))

    # if isgroup == None:
    #     #如果是好友私信
    #     pass
    # else:
    #如果是群聊消息
    if revocation_type == 'Picture' or revocation_type == 'Video' or \
        revocation_type == 'Attachment' or revocation_type == 'Recording':

        response = ('@fil@%s' % ('./'+revocation_type+'/' + revocation_msg['msg_filename']), \
                          cheak_group(isgroup)+u'您的好友：%s(%s)，于%s撤回了如下的文件:' \
                          % (revocation_remarkname, revocation_nickname, revocation_time))

        itchat.send_msg(response[1],toUserName='filehelper')
        itchat.send(response[0],toUserName='filehelper')

    elif revocation_type == 'Card' or revocation_type == 'Map' or \
        revocation_type == 'Text' or revocation_type == 'Friends':
        response = cheak_group(isgroup)+u'您的好友：%s(%s)，于%s撤回了如下的消息：\n\n[%s]: %s'\
                        %(revocation_remarkname,revocation_nickname,revocation_time,\
                          revocation_msg_time,revocation_msg['msg_content'])

        itchat.send_msg(response,toUserName='filehelper')

    elif revocation_type == 'Sharing':
        response = cheak_group(isgroup)+u'您的好友：%s(%s)，于%s撤回了如下的消息：\n\n[%s]: 标题：%s\n链接url：%s'\
                   %(revocation_remarkname,revocation_nickname,revocation_time, \
                     revocation_msg_time,revocation_msg['msg_content'],revocation_msg['msg_url'])

        itchat.send_msg(response,toUserName='filehelper')


def cheak_group(isgroup):
    if isgroup == None:
    #如果为私信
        res_heard = ''
    else:
    #如果为群消息
        res_heard = u'群名：%s\n\n'%isgroup

    return res_heard