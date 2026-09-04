import { load } from 'cheerio';
import pMap from 'p-map';

import type { Route } from '@/types';
import cache from '@/utils/cache';
import got from '@/utils/got';
import { parseDate } from '@/utils/parse-date';
import timezone from '@/utils/timezone';

const rootUrl = 'https://hlj.rednet.cn';

export const route: Route = {
    path: '/channel/:id',
    categories: ['traditional-media'],
    example: '/rednet/channel/8288',
    parameters: { id: '栏目 id，可在栏目页 URL 中找到，如 channel/8288.html 即「马上评论」' },
    features: {
        requireConfig: false,
        requirePuppeteer: false,
        antiCrawler: false,
        supportBT: false,
        supportPodcast: false,
        supportScihub: false,
    },
    name: '红辣椒评论栏目',
    maintainers: ['nczitzk'],
    radar: [
        {
            source: ['hlj.rednet.cn/channel/:id'],
            target: '/rednet/channel/:id',
        },
    ],
    handler,
};

async function handler(ctx) {
    const id = ctx.req.param('id');
    const url = `${rootUrl}/channel/${id}.html`;

    const { data: response } = await got(url);
    const $ = load(response);

    // 兼容两种模板：旧版 #div_newsList（带完整时间），新版 ul.main995.list-all（含作者/摘要）
    const newTemplate = $('#div_newsList ul.news_list li').length === 0;
    const list = (newTemplate ? $('ul.main995.list-all li') : $('#div_newsList ul.news_list li'))
        .toArray()
        .map((item) => {
            const $item = $(item);
            if (newTemplate) {
                const link = new URL($item.find('h1 a').attr('href') ?? '', url).href;
                return {
                    title: $item.find('h1 a').attr('title') || $item.find('h1 a').text().trim(),
                    link,
                    author: $item.find('span.zuozhe').text().trim(),
                    pubDate: timezone(parseDate($item.find('span.shijian').text().trim()), 8),
                };
            }
            const link = new URL($item.find('a').attr('href') ?? '', url).href;
            return {
                title: $item.find('a span.f_left').text().trim(),
                link,
                pubDate: timezone(parseDate($item.find('a span.f_right.time').text().trim()), 8),
            };
        });

    const items = await pMap(
        list,
        (item) =>
            cache.tryGet(item.link, async () => {
                const { data: detailResponse } = await got(item.link);
                const $detail = load(detailResponse);

                return {
                    ...item,
                    title: $detail('h1').first().text().trim() || item.title,
                    author: $detail('#author_baidu').text().replace(/^作者：/, '').trim(),
                    description: $detail('div.detail_article_content').html() ?? '',
                };
            }),
        { concurrency: 3 }
    );

    return {
        title: $('title').text(),
        link: url,
        item: items,
    };
}
