/**
 * 通用知识图谱 EML 生成脚本
 * 生成 ~100 条知识（概念 + 关系），覆盖自然科学、中国历史、世界地理、文化艺术、现代科技、数学逻辑六大领域。
 *
 * 使用：npx tsx scripts/generate-general-knowledge.ts
 */

import { buildEMLGraph, serializeEML } from '../src/api/distiller'
import type { DistillConcept, DistillRelation } from '../src/types'
import { writeFileSync, mkdirSync, existsSync } from 'fs'
import { join, dirname } from 'path'
import { fileURLToPath } from 'url'

const __dirname = dirname(fileURLToPath(import.meta.url))
const publicDir = join(__dirname, '..', 'public')

/** 概念定义：concept, importance(0-1), frequency(0+), context */
const concepts: DistillConcept[] = [
  // ─── 自然科学（12 个概念）───
  { concept: '太阳', importance: 0.95, context: '恒星，太阳系中心', frequency: 10 },
  { concept: '地球', importance: 0.95, context: '太阳系第三行星', frequency: 10 },
  { concept: '月球', importance: 0.85, context: '地球的天然卫星', frequency: 8 },
  { concept: '万有引力', importance: 0.90, context: '四大基本力之一', frequency: 9 },
  { concept: '光速', importance: 0.88, context: '约 3×10^8 m/s', frequency: 8 },
  { concept: '相对论', importance: 0.92, context: '爱因斯坦的时空理论', frequency: 9 },
  { concept: '原子', importance: 0.90, context: '物质的基本单位', frequency: 9 },
  { concept: '分子', importance: 0.85, context: '由原子组成的粒子', frequency: 8 },
  { concept: 'DNA', importance: 0.90, context: '脱氧核糖核酸，遗传物质', frequency: 9 },
  { concept: '进化论', importance: 0.88, context: '达尔文的自然选择学说', frequency: 8 },
  { concept: '元素周期表', importance: 0.82, context: '门捷列夫的元素分类', frequency: 7 },
  { concept: '量子力学', importance: 0.90, context: '微观世界的物理理论', frequency: 9 },

  // ─── 中国历史（11 个概念）───
  { concept: '中国', importance: 0.95, context: '东亚文明古国', frequency: 12 },
  { concept: '秦朝', importance: 0.85, context: '中国第一个大一统王朝', frequency: 8 },
  { concept: '汉朝', importance: 0.82, context: '继秦之后的强盛王朝', frequency: 7 },
  { concept: '唐朝', importance: 0.88, context: '中国古代鼎盛时期', frequency: 9 },
  { concept: '四大发明', importance: 0.80, context: '造纸术、印刷术、火药、指南针', frequency: 7 },
  { concept: '丝绸之路', importance: 0.78, context: '古代东西方贸易通道', frequency: 7 },
  { concept: '长城', importance: 0.82, context: '中国古代防御工程', frequency: 8 },
  { concept: '史记', importance: 0.75, context: '司马迁的历史著作', frequency: 6 },
  { concept: '孔子', importance: 0.85, context: '儒家学派创始人', frequency: 8 },
  { concept: '科举制度', importance: 0.72, context: '中国古代选拔官员制度', frequency: 6 },
  { concept: '四大名著', importance: 0.70, context: '红楼梦、三国演义、西游记、水浒传', frequency: 5 },

  // ─── 世界地理（10 个概念）───
  { concept: '亚洲', importance: 0.85, context: '世界最大洲', frequency: 8 },
  { concept: '欧洲', importance: 0.82, context: '西方文明发源地', frequency: 7 },
  { concept: '非洲', importance: 0.82, context: '热带大陆', frequency: 7 },
  { concept: '太平洋', importance: 0.80, context: '世界最大洋', frequency: 7 },
  { concept: '喜马拉雅山脉', importance: 0.78, context: '世界最高山脉', frequency: 6 },
  { concept: '尼罗河', importance: 0.72, context: '世界最长河流', frequency: 5 },
  { concept: '撒哈拉沙漠', importance: 0.72, context: '世界最大热沙漠', frequency: 5 },
  { concept: '地中海', importance: 0.70, context: '欧亚非之间的内陆海', frequency: 5 },
  { concept: '赤道', importance: 0.75, context: '地球纬线 0°', frequency: 6 },
  { concept: '南极洲', importance: 0.78, context: '地球最南端大陆', frequency: 6 },

  // ─── 文化与艺术（11 个概念）───
  { concept: '汉语', importance: 0.85, context: '世界上使用人数最多的语言', frequency: 9 },
  { concept: '英语', importance: 0.82, context: '国际通用语言', frequency: 8 },
  { concept: '莎士比亚', importance: 0.78, context: '英国文学巨匠', frequency: 7 },
  { concept: '贝多芬', importance: 0.80, context: '德国作曲家，古典音乐', frequency: 7 },
  { concept: '文艺复兴', importance: 0.82, context: '14-17世纪欧洲文化运动', frequency: 7 },
  { concept: '达芬奇', importance: 0.78, context: '意大利文艺复兴巨匠', frequency: 7 },
  { concept: '蒙娜丽莎', importance: 0.75, context: '达芬奇名画', frequency: 6 },
  { concept: '交响乐', importance: 0.72, context: '大型管弦乐作品形式', frequency: 6 },
  { concept: '文学', importance: 0.80, context: '以语言为媒介的艺术', frequency: 8 },
  { concept: '绘画', importance: 0.78, context: '视觉艺术的主要形式', frequency: 7 },
  { concept: '古典音乐', importance: 0.72, context: '西方艺术音乐传统', frequency: 6 },

  // ─── 现代科技（10 个概念）───
  { concept: '计算机', importance: 0.90, context: '电子计算设备', frequency: 10 },
  { concept: '互联网', importance: 0.92, context: '全球计算机网络', frequency: 10 },
  { concept: '人工智能', importance: 0.95, context: '模拟人类智能的技术', frequency: 10 },
  { concept: '智能手机', importance: 0.88, context: '移动计算通信设备', frequency: 9 },
  { concept: '芯片', importance: 0.85, context: '集成电路，计算机核心', frequency: 8 },
  { concept: '5G', importance: 0.80, context: '第五代移动通信技术', frequency: 8 },
  { concept: '大数据', importance: 0.82, context: '海量数据处理技术', frequency: 8 },
  { concept: '云计算', importance: 0.82, context: '远程计算资源服务', frequency: 8 },
  { concept: '区块链', importance: 0.78, context: '去中心化分布式账本', frequency: 7 },
  { concept: '物联网', importance: 0.80, context: '万物互联的网络', frequency: 7 },

  // ─── 数学与逻辑（9 个概念）───
  { concept: '数学', importance: 0.88, context: '研究数量、结构、变化的学科', frequency: 9 },
  { concept: '勾股定理', importance: 0.75, context: '直角三角形边长关系', frequency: 6 },
  { concept: '圆周率', importance: 0.78, context: 'π ≈ 3.14159', frequency: 7 },
  { concept: '微积分', importance: 0.82, context: '牛顿莱布尼茨创立', frequency: 7 },
  { concept: '概率论', importance: 0.78, context: '研究随机现象的数学', frequency: 7 },
  { concept: '逻辑学', importance: 0.75, context: '推理规则的形式化研究', frequency: 6 },
  { concept: '图论', importance: 0.72, context: '研究图结构的数学分支', frequency: 6 },
  { concept: '代数', importance: 0.80, context: '符号运算的数学分支', frequency: 7 },
  { concept: '几何', importance: 0.80, context: '空间与形状的数学', frequency: 7 },
]

/** 关系定义：src, dst, type('causes'|'related_to'|'inspired_by'), strength(0-1) */
const relations: DistillRelation[] = [
  // ─── 自然科学（8 条关系）───
  { src: '太阳', dst: '地球', type: 'causes', strength: 0.90 },
  { src: '地球', dst: '月球', type: 'causes', strength: 0.85 },
  { src: '万有引力', dst: '相对论', type: 'inspired_by', strength: 0.80 },
  { src: '原子', dst: '分子', type: 'related_to', strength: 0.85 },
  { src: 'DNA', dst: '进化论', type: 'related_to', strength: 0.80 },
  { src: '量子力学', dst: '原子', type: 'related_to', strength: 0.82 },
  { src: '光速', dst: '相对论', type: 'related_to', strength: 0.88 },
  { src: '元素周期表', dst: '原子', type: 'related_to', strength: 0.75 },

  // ─── 中国历史（7 条关系）───
  { src: '秦朝', dst: '中国', type: 'causes', strength: 0.85 },
  { src: '汉朝', dst: '秦朝', type: 'related_to', strength: 0.80 },
  { src: '唐朝', dst: '丝绸之路', type: 'causes', strength: 0.82 },
  { src: '四大发明', dst: '中国', type: 'related_to', strength: 0.78 },
  { src: '长城', dst: '秦朝', type: 'related_to', strength: 0.80 },
  { src: '孔子', dst: '中国', type: 'causes', strength: 0.82 },
  { src: '科举制度', dst: '汉朝', type: 'related_to', strength: 0.72 },

  // ─── 世界地理（7 条关系）───
  { src: '亚洲', dst: '中国', type: 'related_to', strength: 0.85 },
  { src: '喜马拉雅山脉', dst: '亚洲', type: 'related_to', strength: 0.80 },
  { src: '尼罗河', dst: '非洲', type: 'related_to', strength: 0.75 },
  { src: '撒哈拉沙漠', dst: '非洲', type: 'related_to', strength: 0.75 },
  { src: '地中海', dst: '欧洲', type: 'related_to', strength: 0.70 },
  { src: '赤道', dst: '非洲', type: 'related_to', strength: 0.72 },
  { src: '太平洋', dst: '亚洲', type: 'related_to', strength: 0.78 },

  // ─── 文化与艺术（5 条关系）───
  { src: '莎士比亚', dst: '文学', type: 'causes', strength: 0.82 },
  { src: '贝多芬', dst: '交响乐', type: 'causes', strength: 0.80 },
  { src: '达芬奇', dst: '蒙娜丽莎', type: 'causes', strength: 0.85 },
  { src: '达芬奇', dst: '文艺复兴', type: 'related_to', strength: 0.80 },
  { src: '贝多芬', dst: '古典音乐', type: 'related_to', strength: 0.82 },

  // ─── 现代科技（5 条关系）───
  { src: '人工智能', dst: '计算机', type: 'related_to', strength: 0.90 },
  { src: '互联网', dst: '智能手机', type: 'related_to', strength: 0.85 },
  { src: '芯片', dst: '计算机', type: 'causes', strength: 0.88 },
  { src: '5G', dst: '物联网', type: 'causes', strength: 0.82 },
  { src: '云计算', dst: '大数据', type: 'related_to', strength: 0.85 },

  // ─── 数学与逻辑（4 条关系）───
  { src: '勾股定理', dst: '几何', type: 'related_to', strength: 0.82 },
  { src: '微积分', dst: '数学', type: 'related_to', strength: 0.85 },
  { src: '图论', dst: '数学', type: 'related_to', strength: 0.78 },
  { src: '概率论', dst: '数学', type: 'related_to', strength: 0.75 },

  // ─── 跨领域链接（4 条关系）───
  { src: '中国', dst: '汉语', type: 'related_to', strength: 0.90 },
  { src: '中国', dst: '亚洲', type: 'related_to', strength: 0.85 },
  { src: '地球', dst: '万有引力', type: 'related_to', strength: 0.82 },
  { src: '人工智能', dst: '逻辑学', type: 'related_to', strength: 0.78 },
]

async function main() {
  console.log('🔨 开始构建通用知识图谱…')
  console.log(`   概念：${concepts.length} 个`)
  console.log(`   关系：${relations.length} 条`)
  console.log(`   知识条数：${concepts.length + relations.length} 条\n`)

  // 构建 EML 图
  const graph = await buildEMLGraph(concepts, relations)

  // 序列化为二进制
  const buffer = serializeEML(graph)

  // 确保 public 目录存在
  if (!existsSync(publicDir)) {
    mkdirSync(publicDir, { recursive: true })
  }

  // 写入 EML 文件
  const emlPath = join(publicDir, 'general_knowledge_distilled.eml')
  writeFileSync(emlPath, Buffer.from(buffer))
  console.log(`✅ 已写入：${emlPath} (${(buffer.byteLength / 1024).toFixed(1)} KB)`)

  // 写入概念名 JSON（用于前端替换 concept_0 占位符）
  const conceptsJson = {
    concepts: graph.vertices.map(v => ({ id: v.id, concept: v.label }))
  }
  const jsonPath = join(publicDir, 'general_knowledge_distilled.concepts.json')
  writeFileSync(jsonPath, JSON.stringify(conceptsJson, null, 2))
  console.log(`✅ 已写入：${jsonPath}`)

  console.log(`\n📊 统计：`)
  console.log(`   V（概念/顶点）= ${graph.vertices.length}`)
  console.log(`   E（关系/边）  = ${graph.edges.length}`)
  console.log(`   K（知识条数）  = ${graph.vertices.length + graph.edges.length}`)
  const avgDelta = graph.vertices.reduce((s, v) => s + v.delta, 0) / graph.vertices.length
  console.log(`   𝕀̄（平均信息存在度）= ${avgDelta.toFixed(4)}`)
  console.log(`\n🎉 通用知识图谱生成完毕！`)
}

main().catch(err => {
  console.error('❌ 生成失败：', err)
  process.exit(1)
})
