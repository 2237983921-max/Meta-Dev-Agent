const DATA = {
  kols: [
    { name: "CryptoGuru", handle: "@CryptoGuru_X", avatar: "🦊", followers: "2.1M", influence: 95 },
    { name: "DegenSpartan", handle: "@DegenSpartan", avatar: "⚔️", followers: "890K", influence: 88 },
    { name: "MoonCarl", handle: "@MoonCarl", avatar: "🌙", followers: "1.5M", influence: 92 },
    { name: "CryptoWizardd", handle: "@CryptoWizardd", avatar: "🧙", followers: "750K", influence: 85 },
    { name: "SolanaLegend", handle: "@SolanaLegend", avatar: "☀️", followers: "620K", influence: 82 },
    { name: "PumpDetector", handle: "@PumpDetector", avatar: "📡", followers: "340K", influence: 78 },
    { name: "AlphaCalls", handle: "@AlphaCalls", avatar: "🎯", followers: "1.2M", influence: 90 },
    { name: "DeFi_Degen", handle: "@DeFi_Degen", avatar: "🔥", followers: "520K", influence: 80 },
    { name: "GemHunterX", handle: "@GemHunterX", avatar: "💎", followers: "430K", influence: 76 },
    { name: "WhaleAlert", handle: "@WhaleAlertCrypto", avatar: "🐋", followers: "3.1M", influence: 97 }
  ],
  normalUsers: [
    { name: "crypto_andy", handle: "@crypto_andy92", avatar: "🐸" },
    { name: "SolTrader", handle: "@SolTrader01", avatar: "📈" },
    { name: "memeLord", handle: "@memeLord420", avatar: "🤡" },
    { name: "degenKing", handle: "@degenKing_sol", avatar: "👑" },
    { name: "pumpItUp", handle: "@pumpItUp69", avatar: "🚀" },
    { name: "basedfren", handle: "@basedfren_", avatar: "🫡" },
    { name: "apeCaller", handle: "@apeCaller", avatar: "🦍" },
    { name: "chad_trader", handle: "@chad_trader", avatar: "💪" },
    { name: "rugged_again", handle: "@rugged_again", avatar: "💀" },
    { name: "moonboy", handle: "@moonboy_sol", avatar: "🌕" },
    { name: "token_sniper", handle: "@token_sniper_", avatar: "🎯" },
    { name: "cryptoSally", handle: "@cryptoSally", avatar: "👩‍💻" },
    { name: "SOLmaxi", handle: "@SOLmaxi", avatar: "☀️" },
    { name: "ETHbull", handle: "@ETHbull_", avatar: "🐂" },
    { name: "onchain_monk", handle: "@onchain_monk", avatar: "🧘" }
  ],
  narratives: [
    "动物系",
    "AI Meme",
    "Base 热门",
    "政治梗",
    "Solana 梗图",
    "社区自传播",
    "Whale 追随",
    "Pump.fun 毕业"
  ],
  knownTokens: [
    { symbol: "$PEPE", name: "Pepe", icon: "🐸", chain: "ETH", mentions: 5420, sentiment: 72, narrative: "动物系" },
    { symbol: "$WIF", name: "dogwifhat", icon: "🎩", chain: "SOL", mentions: 3210, sentiment: 81, narrative: "Solana 梗图" },
    { symbol: "$BONK", name: "Bonk", icon: "🐕", chain: "SOL", mentions: 2890, sentiment: 68, narrative: "Solana 梗图" },
    { symbol: "$POPCAT", name: "Popcat", icon: "🐱", chain: "SOL", mentions: 1920, sentiment: 85, narrative: "动物系" },
    { symbol: "$FLOKI", name: "Floki", icon: "⚡", chain: "ETH", mentions: 1650, sentiment: 60, narrative: "社区自传播" },
    { symbol: "$MYRO", name: "Myro", icon: "🐶", chain: "SOL", mentions: 890, sentiment: 74, narrative: "动物系" },
    { symbol: "$MEW", name: "cat in a dogs world", icon: "😺", chain: "SOL", mentions: 780, sentiment: 79, narrative: "Solana 梗图" },
    { symbol: "$BRETT", name: "Brett", icon: "🧢", chain: "BASE", mentions: 650, sentiment: 71, narrative: "Base 热门" }
  ],
  newTokenTemplates: [
    { symbol: "$GROK", name: "GROK AI", icon: "🤖", chain: "SOL", narrative: "AI Meme" },
    { symbol: "$NEIRO", name: "Neiro", icon: "🐕‍🦺", chain: "ETH", narrative: "动物系" },
    { symbol: "$MOODENG", name: "Moo Deng", icon: "🦛", chain: "SOL", narrative: "动物系" },
    { symbol: "$PNUT", name: "Peanut", icon: "🥜", chain: "SOL", narrative: "社区自传播" },
    { symbol: "$GOAT", name: "Goatseus Maximus", icon: "🐐", chain: "SOL", narrative: "政治梗" },
    { symbol: "$SPX", name: "SPX6900", icon: "📊", chain: "ETH", narrative: "社区自传播" },
    { symbol: "$SIGMA", name: "Sigma", icon: "🗿", chain: "SOL", narrative: "社区自传播" },
    { symbol: "$RIZZ", name: "Rizz", icon: "😏", chain: "SOL", narrative: "Pump.fun 毕业" },
    { symbol: "$HAWK", name: "Hawk Tuah", icon: "🦅", chain: "SOL", narrative: "政治梗" },
    { symbol: "$QUANT", name: "QuantCat", icon: "🐈", chain: "SOL", narrative: "AI Meme" },
    { symbol: "$FWOG", name: "Fwog", icon: "🐸", chain: "SOL", narrative: "Pump.fun 毕业" },
    { symbol: "$LUCE", name: "LUCE", icon: "✨", chain: "SOL", narrative: "社区自传播" }
  ],
  tweetTemplates: {
    kolShill: [
      "🚀 刚加仓 {token}，社区共识比我预期更强，聪明钱已经在路上。",
      "如果你还没把 {token} 放进观察列表，现在可能已经晚了半拍。",
      "{token} 的叙事有点像上一轮爆发前的 $WIF，情绪和图形都在共振。",
      "我盯了 {token} 两周，社区、传播和流动性都比大多数新币完整。",
      "📢 {token} 刚突破一段整理区间，量能和讨论度一起抬头了。"
    ],
    normalMention: [
      "{token} 怎么突然满时间线都是，真的是今天的主角吗？",
      "刚看到 {token} 上了好几个群，谁研究过团队背景？",
      "{token} 这波走势有点离谱，我是不是又要 FOMO 了。",
      "有人在盯 {token} 吗？感觉社区传播速度明显比平均新币快。",
      "Dex 上刷到 {token}，流动性暂时看着还行。"
    ],
    pumpFun: [
      "🆕 Pump.fun 上新了 {token}，持有人增长很快。",
      "{token} 刚从 pump.fun 毕业，开始往主流 DEX 迁移。",
      "狙击地址正在围绕 {token} 进出，节奏很快，谨慎看待。",
      "{token} 在 pump.fun 上已经冲到前排，聊天量也跟上了。"
    ],
    whaleAlert: [
      "🐋 一笔大额买单扫进 {token}，疑似聪明钱试探仓位。",
      "3 个胜率很高的钱包刚刚同时碰了 {token}。",
      "顶级地址在增持 {token}，短线热度可能继续外溢。"
    ],
    generalCrypto: [
      "{token} 的叙事和 AI + meme 的混合风格有点对当下胃口。",
      "今天 Solana meme 很热，{token} 在其中算是更像样的一个。",
      "如果市场风险偏好继续抬升，{token} 可能受益明显。",
      "不少人把 {token} 当成轮动接力的候选币在看。"
    ]
  }
};

const CHAIN_COLORS = {
  SOL: "#9f7bff",
  ETH: "#6f8cff",
  BASE: "#59c3ff"
};

function pickRandom(list) {
  return list[Math.floor(Math.random() * list.length)];
}

function randomInt(min, max) {
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

function randomFloat(min, max, digits = 2) {
  return Number((Math.random() * (max - min) + min).toFixed(digits));
}

function chance(probability) {
  return Math.random() < probability;
}

function generateSparklineData(length = 20, seed = randomFloat(25, 78, 1)) {
  const points = [];
  let value = seed;

  for (let index = 0; index < length; index += 1) {
    value += (Math.random() - 0.42) * 12;
    value = Math.max(5, Number(value.toFixed(2)));
    points.push(value);
  }

  return points;
}

function createMetricSeed(baseMentions) {
  return {
    marketCap: randomInt(180000, 36000000) + baseMentions * 420,
    volume24h: randomInt(90000, 4800000) + baseMentions * 95,
    holders: randomInt(180, 28000),
    scoreBias: randomInt(48, 89)
  };
}

function buildTokenProfile(token) {
  const metrics = createMetricSeed(token.mentions || randomInt(30, 600));
  return {
    ...token,
    mentions: token.mentions || randomInt(10, 120),
    sentiment: token.sentiment || randomInt(52, 86),
    sparkline: generateSparklineData(22, randomFloat(22, 70, 1)),
    marketCap: token.marketCap || metrics.marketCap,
    volume24h: token.volume24h || metrics.volume24h,
    holders: token.holders || metrics.holders,
    narrative: token.narrative || pickRandom(DATA.narratives),
    scoreBias: token.scoreBias || metrics.scoreBias
  };
}

function generateRandomTweet() {
  const isKol = chance(0.22);
  const isNewToken = chance(0.15);
  const isWhale = !isKol && chance(0.08);

  let user;
  let templateGroup;

  if (isWhale) {
    user = { name: "Whale Alert", handle: "@whale_alert", avatar: "🐋", followers: "3.1M", isKol: true };
    templateGroup = "whaleAlert";
  } else if (isKol) {
    user = { ...pickRandom(DATA.kols), isKol: true };
    templateGroup = "kolShill";
  } else {
    user = { ...pickRandom(DATA.normalUsers), isKol: false };
    templateGroup = pickRandom(["normalMention", "normalMention", "pumpFun", "generalCrypto"]);
  }

  const tokenSource = isNewToken ? DATA.newTokenTemplates : DATA.knownTokens;
  const rawToken = { ...pickRandom(tokenSource), isNew: isNewToken };
  const token = buildTokenProfile(rawToken);
  const text = pickRandom(DATA.tweetTemplates[templateGroup]).replace(/\{token\}/g, token.symbol);

  const likes = isKol ? randomInt(450, 5600) : randomInt(6, 320);
  const retweets = isKol ? randomInt(120, 1900) : randomInt(1, 80);
  const replies = randomInt(0, isKol ? 200 : 30);

  return {
    id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    user,
    text,
    token,
    likes,
    retweets,
    replies,
    engagement: likes + retweets * 2 + replies * 3,
    isKol: Boolean(user.isKol),
    isNewToken,
    isWhale,
    narrative: token.narrative,
    timestamp: new Date()
  };
}
