import time
import pandas as pd
import random
import requests
from lxml import etree
import csv

headers = {
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36 Edg/135.0.0.0',
}

# def style_name_get():
#     url = 'https://www.dongchedi.com'
#     style_name_response = requests.get(url, headers=headers)
#     style_name_response.close()
#
#     style_name_page_tree = etree.HTML(style_name_response.text)
#     div_list = style_name_page_tree.xpath('//*[@id="__next"]/div/div[2]/div[1]/div/div/div[1]/div[1]')
#
#     for div in div_list:
#         style_name_list = div.xpath('.//a//text()')
#         href_list = [url + href for href in div.xpath('.//a/@href')]
#
#     return style_name_list, href_list
#
# def car_id_get(href_list):
#     new_url = 'https://www.dongchedi.com/motor/pc/car/brand/select_series_v2?aid=1839&app_name=auto_web_pc'
#     car_ids = []
#
#     for i in range(1, len(href_list)):
#         temp = []
# #         flag = 0
# #         series_type = href_list[i].split('-')[1]
# #         for j in range(1, 200):
# #             data = {
# #                 'series_type': series_type,
# #                 'sort_new': 'hot_desc',
# #                 'city_name': '重庆',
# #                 'limit': 30,
# #                 'page': j,
# #             }
# #             new_res = requests.post(new_url, headers=headers, data=data)
# #             new_res.close()
# #
# #             for series in new_res.json()['data']['series']:
# #                 temp.append(series['id'])
# #
# #             if flag == temp[-1]:
# #                 car_ids.append(temp)
# #                 print('ok!')
# #                 print(len(temp))
# #                 break
# #             else:
# #                 flag = temp[-1]
# #
# #             print(temp[-1], j)
# #
# #             time.sleep(random.randint(1, 3))
# #
# #     return car_ids      print(i)
#

def car_info_get(car_id):
    k = 0
    first_url = 'https://www.dongchedi.com/auto/series/'
    k += 1
    car_res = requests.get(first_url + car_id, headers=headers)
    car_res.close()
    car_info_tree = etree.HTML(car_res.text)

    try:
        car_name = car_info_tree.xpath('//*[@id="__next"]/div/div[2]/div[2]/div[1]/div[1]/div[1]/h1/text()')[0]
    except:
        car_name = '暂无'

    print(car_name, car_id)

    try:
        brand, temp, size = car_info_tree.xpath('//*[@id="__next"]/div/div[2]/div[2]/div[1]/div[1]/div[1]/span/text()')
    except:
        brand = '暂无'
        size = '暂无'

    try:
        agent_price = car_info_tree.xpath('//*[@id="__next"]/div/div[2]/div[2]/div[1]/div[1]/div[2]/p[2]/text()')[0]
    except:
        agent_price = '暂无'

    try:
        facture_price = car_info_tree.xpath('//*[@id="__next"]/div/div[2]/div[2]/div[1]/div[1]/p/span[2]/text()')[0]
    except:
        facture_price = '暂无'

    try:
        acceleration = car_info_tree.xpath('//*[@id="__next"]/div/div[2]/div[2]/div[3]/div[2]/div[2]/div[2]/div/section[2]/div/div/div[1]/section/article/div[1]/span[2]/text()')[0]
    except:
        acceleration = '暂无'

    try:
        energy_type = car_info_tree.xpath('//*[@id="__next"]/div/div[2]/div[2]/div[3]/div[2]/div[2]/div[2]/div/section[2]/div/div/div[1]/section/article/div[2]/span[2]/text()')[0]
    except:
        energy_type = '暂无'

    try:
        engine = car_info_tree.xpath('//*[@id="__next"]/div/div[2]/div[2]/div[3]/div[2]/div[2]/div[2]/div/section[2]/div/div/div[1]/section/article/div[3]/span[2]/text()')[0]
    except:
        engine = '暂无'

    try:
        transmission = car_info_tree.xpath('//*[@id="__next"]/div/div[2]/div[2]/div[3]/div[2]/div[2]/div[2]/div/section[2]/div/div/div[1]/section/article/div[4]/span[2]/text()')[0]
    except:
        transmission = '暂无'

    try:
        score_url = 'https://www.dongchedi.com/auto/series/score/' + str(car_id) + '-x-x-x-x-x-x'
        score_res = requests.get(score_url, headers=headers)
        score_res.close()

        score_tree = etree.HTML(score_res.text)

        a = score_tree.xpath('//*[@id="__next"]/div/div[2]/div[2]/section[1]/div/div[2]/div[2]/ul[1]//text()')[1]
        b = score_tree.xpath('//*[@id="__next"]/div/div[2]/div[2]/section[1]/div/div[2]/div[2]/ul[2]//text()')[1]
        c = score_tree.xpath('//*[@id="__next"]/div/div[2]/div[2]/section[1]/div/div[2]/div[2]/ul[3]//text()')[1]
        d = score_tree.xpath('//*[@id="__next"]/div/div[2]/div[2]/section[1]/div/div[2]/div[2]/ul[4]//text()')[1]
        e = score_tree.xpath('//*[@id="__next"]/div/div[2]/div[2]/section[1]/div/div[2]/div[2]/ul[5]//text()')[1]
        f = score_tree.xpath('//*[@id="__next"]/div/div[2]/div[2]/section[1]/div/div[2]/div[2]/ul[6]//text()')[1]
        g = score_tree.xpath('//*[@id="__next"]/div/div[2]/div[2]/section[1]/div/div[2]/div[2]/ul[7]//text()')[1]
        h = score_tree.xpath('//*[@id="__next"]/div/div[2]/div[2]/section[1]/div/div[2]/div[2]/ul[8]//text()')[1]
    except:
        a = '暂无'
        b = '暂无'
        c = '暂无'
        d = '暂无'
        e = '暂无'
        f = '暂无'
        g = '暂无'
        h = '暂无'

    return car_name, brand, size, agent_price, facture_price, acceleration, energy_type, engine, transmission, a, b, c, d, e, f, g, h




if __name__ == '__main__':

    # style_name_list, href_list = style_name_get()
    # print(href_list)
    # car_ids = car_id_get(href_list)
    # print(car_ids)
    #
    # f = open('car_ids.csv', 'w', newline='', encoding='gbk')
    # csv_writer = csv.writer(f)
    #
    # with open('car_id.txt', 'w', encoding='utf-8') as f:
    #     for i in range(1, len(style_name_list)):
    #         for j in range(len(car_ids[i - 1])):
    #             csv_writer.writerow([car_ids[i - 1][j]])
    #
    # f.close()

    #
    # for i in range(1, len(style_name_list)):
    #     car_info_get(style_name_list[i], car_ids[i - 1])
    #     print(style_name_list[i], '完成!')
    car_names, brands, sizes, agent_prices, facture_prices, accelerations, energy_types, engines, transmissions, comprehensive_score, appearance_score, interior_score, configuration_score, space_score, comfort_score, manipulate_score, power_score = [], [], [], [], [], [], [], [], [], [], [], [], [], [], [], [], []

    csv_reader = csv.reader(open('car_ids.csv'))
    for row in csv_reader:
        t1 = time.time()
        car_name, brand, size, agent_price, facture_price, acceleration, energy_type, engine, transmission, a, b, c, d, e, f, g, h = car_info_get(row[0])

        car_names.append(car_name)
        brands.append(brand)
        sizes.append(size)
        agent_prices.append(agent_price)
        facture_prices.append(facture_price)
        accelerations.append(acceleration)
        energy_types.append(energy_type)
        engines.append(engine)
        transmissions.append(transmission)
        comprehensive_score.append(a)
        appearance_score.append(b)
        interior_score.append(c)
        configuration_score.append(d)
        space_score.append(e)
        comfort_score.append(f)
        manipulate_score.append(g)
        power_score.append(h)
        t2 = time.time()

        time.sleep(2)

    data = list(
        zip(car_names, brands, sizes, agent_prices, facture_prices, accelerations, energy_types, engines, transmissions,
            comprehensive_score, appearance_score, interior_score, configuration_score, space_score, comfort_score,
            manipulate_score, power_score))
    df = pd.DataFrame(data,
                      columns=['车名', '品牌', '车型', '经销商报价', '厂商指导价', '百公里加速', '能源类型', '发动机',
                               '变速箱', '综合评分', '外观评分', '内饰评分', '配置评分', '空间评分', '舒适性评分',
                               '操纵评分', '动力评分'])
    df.to_excel('car_info.xlsx', index=False)