import { load } from 'cheerio';

import type { Route } from '@/types';
import cache from '@/utils/cache';
import got from '@/utils/got';
import { parseDate } from '@/utils/parse-date';

const rootUrl = 'https://zjnews.zjol.com.cn/zjxc';

export const route: Route = {
    path: '/zjxc',
    categories: ['traditional-media'],
    example: '/zjol/zjxc',
    features: {
        requireConfig: false,
        requirePuppeteer: false,
        antiCrawler: false,
        supportBT: false,
        supportPodcast: false,
        supportScihub: false,
    },
    name: '浙江宣传',
    maintainers: ['nczitzk'],
    radar: [
        {
            source: ['zjnews.zjol.com.cn/zjxc'],
            target: '/zjol/zjxc',
        },
    ],
    handler,
};

async function handler() {
    const response = await got({
        method: 'get',
        url: `${rootUrl}/index.shtml`,
    });
    const $ = load(response.data);

    const list = $('ul.listUl li.listLi')
        .toArray()
        .map((item) => {
            const $item = $(item);
            const link = new URL($item.find('a').attr('href') ?? '', rootUrl).href;
            return {
                title: $item.find('a').text().trim(),
                link,
                pubDate: parseDate($item.find('span.listSpan').text().trim(), 'YYYY年MM月DD日HH时'),
            };
        });

    const items = await Promise.all(
        list.map((item) =>
            cache.tryGet(item.link, async () => {
                const detailResponse = await got({
                    method: 'get',
                    url: item.link,
                });
                const $detail = load(detailResponse.data);

                const info = $detail('div.info span')
                    .toArray()
                    .map((span) => $(span).text().trim());

                return {
                    ...item,
                    title: $detail('h1.artTitle').text().trim(),
                    author: info[1]?.replace(/^来源[：:]\s*/, ''),
                    pubDate: parseDate(info[0], 'YYYY-MM-DD HH:mm:ss'),
                    description: $detail('div.content div.artCon').html() ?? '',
                };
            })
        )
    );

    return {
        title: $('title').text(),
        link: rootUrl,
        item: items,
    };
}
