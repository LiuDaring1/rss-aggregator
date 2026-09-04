import type { Route } from '@/types';
import ofetch from '@/utils/ofetch';

import utils from './utils';

export const route: Route = {
    path: '/studio/:id',
    categories: ['new-media'],
    example: '/thepaper/studio/20',
    parameters: { id: '工作室 id，可在工作室页 URL 中找到，如 studio_20 即「马上评」工作室' },
    features: {
        requireConfig: false,
        requirePuppeteer: false,
        antiCrawler: false,
        supportBT: false,
        supportPodcast: false,
        supportScihub: false,
    },
    name: '工作室',
    maintainers: ['nczitzk', 'bigfei'],
    handler,
    description: `| 工作室 ID | 工作室名 |
| --------- | -------- |
| 20        | 马上评   |`,
};

async function handler(ctx) {
    const id = Number(ctx.req.param('id'));

    const resp = await ofetch('https://api.thepaper.cn/contentapi/studio/detailsPageListWww', {
        method: 'POST',
        body: {
            studioId: id,
            pageNum: 1,
            pageSize: 30,
            startTime: 0,
        },
    });

    const list = resp.data.pageInfo.list ?? [];
    const items = await Promise.all(list.map((item) => utils.ProcessItem(item, ctx)));

    return {
        title: `澎湃新闻 - 工作室 ${ctx.req.param('id')}`,
        link: `https://www.thepaper.cn/studio_${ctx.req.param('id')}`,
        item: items,
        itunes_author: '澎湃新闻',
    };
}
