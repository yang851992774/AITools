"""
PDF生成器
"""
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas
from typing import List, Dict


class PDFGenerator:
    """生成PDF文件"""
    
    def __init__(self):
        """初始化PDF生成器"""
        # 使用Helvetica字体，对于数字和基本运算符足够
        self.font_name = 'Helvetica'
        self.font_size = 15  # 字体大小
        self.title_font_size = 18
        
        # 布局参数
        self.cols = 3  # 3列
        self.rows = 20  # 20行
        self.questions_per_page = self.cols * self.rows  # 60题
    
    def generate_pdf(self, all_pages: List[List[Dict]], output_path: str):
        """
        生成PDF文件
        :param all_pages: 所有页面的题目列表
        :param output_path: 输出文件路径
        """
        c = canvas.Canvas(output_path, pagesize=A4)
        width, height = A4
        
        # 页面边距（优化左右间距）
        margin_left = 2 * cm
        margin_right = 2 * cm
        margin_top = 2.5 * cm
        margin_bottom = 1.5 * cm
        
        # 可用区域
        usable_width = width - margin_left - margin_right
        usable_height = height - margin_top - margin_bottom
        
        # 计算每个单元格的尺寸
        cell_width = usable_width / self.cols
        cell_height = usable_height / self.rows
        
        for page_num, page_questions in enumerate(all_pages):
            # 绘制标题
            title = f"Math Exercises - Page {page_num + 1}"
            c.setFont(self.font_name + '-Bold', self.title_font_size)
            title_width = c.stringWidth(title, self.font_name + '-Bold', self.title_font_size)
            title_x = (width - title_width) / 2
            title_y = height - margin_top + 0.3 * cm
            c.drawString(title_x, title_y, title)
            
            # 题目区域起始Y坐标（从顶部开始）
            questions_start_y = height - margin_top - 1.2 * cm
            
            # 确保每页正好60题
            questions_to_draw = page_questions[:self.questions_per_page]
            
            # 绘制题目
            c.setFont(self.font_name, self.font_size)
            
            # 列之间的间距
            col_spacing = 0.8 * cm
            
            for idx, question in enumerate(questions_to_draw):
                row = idx // self.cols
                col = idx % self.cols
                
                # 计算X位置（列位置，增加左右间距）
                x = margin_left + col * cell_width + col_spacing
                
                # 计算Y位置（行位置，垂直居中）
                # 每行的中心Y坐标
                row_center_y = questions_start_y - (row * cell_height) - (cell_height / 2)
                # 文本的基线Y坐标（考虑字体高度）
                y = row_center_y - (self.font_size * 0.35)  # 调整因子使文本在行中居中
                
                # 绘制题目文本
                question_text = question['question']
                
                # 检查文本宽度，如果太宽则缩小字体
                text_width = c.stringWidth(question_text, self.font_name, self.font_size)
                max_text_width = cell_width - col_spacing * 2
                
                if text_width > max_text_width:
                    # 如果文本太宽，使用较小的字体
                    smaller_font_size = self.font_size - 2
                    c.setFont(self.font_name, smaller_font_size)
                    # 重新计算Y位置以适应较小的字体
                    y = row_center_y - (smaller_font_size * 0.35)
                    c.drawString(x, y, question_text)
                    c.setFont(self.font_name, self.font_size)  # 恢复字体
                else:
                    c.drawString(x, y, question_text)
            
            # 添加新页面
            c.showPage()
        
        c.save()
    
    def generate_answer_pdf(self, all_pages: List[List[Dict]], output_path: str):
        """
        生成答案PDF文件
        :param all_pages: 所有页面的题目列表
        :param output_path: 输出文件路径
        """
        c = canvas.Canvas(output_path, pagesize=A4)
        width, height = A4
        
        # 页面边距（优化左右间距）
        margin_left = 2 * cm
        margin_right = 2 * cm
        margin_top = 2.5 * cm
        margin_bottom = 1.5 * cm
        
        # 可用区域
        usable_width = width - margin_left - margin_right
        usable_height = height - margin_top - margin_bottom
        
        # 计算每个单元格的尺寸
        cell_width = usable_width / self.cols
        cell_height = usable_height / self.rows
        
        for page_num, page_questions in enumerate(all_pages):
            # 绘制标题
            title = f"Math Exercises Answers - Page {page_num + 1}"
            c.setFont(self.font_name + '-Bold', self.title_font_size)
            title_width = c.stringWidth(title, self.font_name + '-Bold', self.title_font_size)
            title_x = (width - title_width) / 2
            title_y = height - margin_top + 0.3 * cm
            c.drawString(title_x, title_y, title)
            
            # 题目区域起始Y坐标（从顶部开始）
            questions_start_y = height - margin_top - 1.2 * cm
            
            # 确保每页正好60题
            questions_to_draw = page_questions[:self.questions_per_page]
            
            # 绘制题目和答案
            c.setFont(self.font_name, self.font_size)
            
            # 列之间的间距
            col_spacing = 0.8 * cm
            
            for idx, question in enumerate(questions_to_draw):
                row = idx // self.cols
                col = idx % self.cols
                
                # 计算X位置（列位置，增加左右间距）
                x = margin_left + col * cell_width + col_spacing
                
                # 计算Y位置（行位置，垂直居中）
                row_center_y = questions_start_y - (row * cell_height) - (cell_height / 2)
                y = row_center_y - (self.font_size * 0.35)
                
                # 绘制题目文本和答案
                question_text = question['question']
                answer = question['answer']
                
                # 将题目中的"___"替换为答案
                answer_text = question_text.replace('___', str(answer))
                
                # 检查文本宽度，如果太宽则缩小字体
                text_width = c.stringWidth(answer_text, self.font_name, self.font_size)
                max_text_width = cell_width - col_spacing * 2
                
                if text_width > max_text_width:
                    # 如果文本太宽，使用较小的字体
                    smaller_font_size = self.font_size - 2
                    c.setFont(self.font_name, smaller_font_size)
                    y = row_center_y - (smaller_font_size * 0.35)
                    c.drawString(x, y, answer_text)
                    c.setFont(self.font_name, self.font_size)  # 恢复字体
                else:
                    c.drawString(x, y, answer_text)
            
            # 添加新页面
            c.showPage()
        
        c.save()
    
    def generate_preview_html(self, all_pages: List[List[Dict]]) -> str:
        """
        生成预览HTML
        :param all_pages: 所有页面的题目列表
        :return: HTML字符串
        """
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>数学练习题预览</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    margin: 20px;
                    background-color: #f5f5f5;
                }
                .page {
                    background: white;
                    padding: 30px;
                    margin-bottom: 30px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    page-break-after: always;
                }
                .page-title {
                    font-size: 20px;
                    font-weight: bold;
                    margin-bottom: 20px;
                    text-align: center;
                }
                .questions-grid {
                    display: grid;
                    grid-template-columns: repeat(3, 1fr);
                    gap: 20px 30px;
                    margin-top: 20px;
                }
                .question {
                    font-size: 15px;
                    padding: 8px;
                    border: 1px solid #ddd;
                    border-radius: 4px;
                }
                @media print {
                    body {
                        background-color: white;
                    }
                    .page {
                        box-shadow: none;
                        margin-bottom: 0;
                    }
                }
            </style>
        </head>
        <body>
        """
        
        for page_num, page_questions in enumerate(all_pages):
            html += f'<div class="page">'
            html += f'<div class="page-title">数学练习题 - 第 {page_num + 1} 页</div>'
            html += '<div class="questions-grid">'
            
            for question in page_questions:
                html += f'<div class="question">{question["question"]}</div>'
            
            html += '</div></div>'
        
        html += """
        </body>
        </html>
        """
        
        return html
