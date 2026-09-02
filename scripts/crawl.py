import requests
from lxml import etree



headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36 Edg/135.0.0.0'}
url = "https://www.dongchedi.com/auto/params-carIds-x-24800"

response = requests.get(url, headers=headers)
response.close()

model_tree = etree.HTML(response.text)


div_list = model_tree.xpath('//*[@id="__next"]/div/div/div/div[2]/div[2]/div')

model_name_div_list = div_list[0].xpath('./div[1]/div')


print(model_name_div_list)
print(len(model_name_div_list))
model_names = []
models = []

for model_name_div in model_name_div_list[1:]:
    model_name = model_name_div.xpath('./div[1]/h1/a/text()')[0]
    print(model_name)
    model_names.append(model_name)

base_info = []

base_info_div_list = div_list[1].xpath("./div")
print(len(base_info_div_list))

for base_info_div in base_info_div_list[1:]:
    part_info_div_list = base_info_div.xpath('./div')
    part_info = []
    print(len(part_info_div_list))
    for part_info_div in part_info_div_list:
        try:
            part_info.append(part_info_div.xpath('.//text()')[0])
        except:
            part_info.append("None")

    if len(part_info) < len(model_names) + 1:
        part_info = []
        part_info.append(base_info_div.xpath("./div[1]//text()")[0])
        info_list = base_info_div.xpath("./div[2]/div/div")
        for info in info_list:
            if info.xpath(".//text()"):
                part_info.append(info.xpath(".//span/following-sibling::text()")[0])
            else:
                part_info.append("None")
        print(part_info)

    base_info.append(part_info.copy())


# print(base_info)
# print(len(base_info))
#
model = {}


for j in range(1, len(model_names)+1):
    model["车名"] = model_names[j-1]
    for i in range(len(base_info)):
        model[base_info[i][0]] = base_info[i][j]
    print(model)
    models.append(model)

print(models)