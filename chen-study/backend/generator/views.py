"""
API视图
"""
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.http import HttpResponse, FileResponse
from .question_generator import QuestionGenerator
from .pdf_generator import PDFGenerator
import tempfile
import os
import atexit
import zipfile


class TemporaryFileResponse(FileResponse):
    """自动清理临时文件的响应类"""
    def __init__(self, file_path, *args, **kwargs):
        super().__init__(open(file_path, 'rb'), *args, **kwargs)
        self.file_path = file_path
    
    def close(self):
        super().close()
        try:
            if os.path.exists(self.file_path):
                os.unlink(self.file_path)
        except:
            pass


@api_view(['POST'])
def generate_preview(request):
    """
    生成题目预览
    POST /api/generate-preview/
    {
        "num_pages": 2,
        "max_value": 20,
        "operations": ["addition", "subtraction", "multiplication", "division"],
        "fill_type": "result",  // "result" 或 "operand"
        "difficulty": 50  // 1-100，默认50
    }
    """
    try:
        num_pages = int(request.data.get('num_pages', 1))
        max_value = int(request.data.get('max_value', 20))
        operations = request.data.get('operations', ['addition', 'subtraction'])
        fill_type = request.data.get('fill_type', 'result')
        difficulty = int(request.data.get('difficulty', 50))
        
        # 验证参数
        if num_pages < 1 or num_pages > 50:
            return Response(
                {'error': '页数必须在1-50之间'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if max_value < 1 or max_value > 100:
            return Response(
                {'error': '最大数值必须在1-100之间'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if difficulty < 1 or difficulty > 100:
            return Response(
                {'error': '难度值必须在1-100之间'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 生成题目
        generator = QuestionGenerator(max_value, difficulty)
        all_pages = generator.generate_questions(num_pages, operations, fill_type)
        
        # 生成预览HTML
        pdf_gen = PDFGenerator()
        html_content = pdf_gen.generate_preview_html(all_pages)
        
        return Response({
            'html': html_content,
            'pages': all_pages
        })
    
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
def generate_pdf(request):
    """
    生成PDF文件
    POST /api/generate-pdf/
    参数同 generate_preview
    """
    try:
        num_pages = int(request.data.get('num_pages', 1))
        max_value = int(request.data.get('max_value', 20))
        operations = request.data.get('operations', ['addition', 'subtraction'])
        fill_type = request.data.get('fill_type', 'result')
        difficulty = int(request.data.get('difficulty', 50))
        
        # 验证参数
        if num_pages < 1 or num_pages > 50:
            return Response(
                {'error': '页数必须在1-50之间'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if max_value < 1 or max_value > 100:
            return Response(
                {'error': '最大数值必须在1-100之间'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if difficulty < 1 or difficulty > 100:
            return Response(
                {'error': '难度值必须在1-100之间'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 生成题目
        generator = QuestionGenerator(max_value, difficulty)
        all_pages = generator.generate_questions(num_pages, operations, fill_type)
        
        # 生成PDF
        pdf_gen = PDFGenerator()
        
        # 创建临时文件用于题目PDF和答案PDF
        temp_questions_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
        temp_questions_path = temp_questions_file.name
        temp_questions_file.close()
        
        temp_answers_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
        temp_answers_path = temp_answers_file.name
        temp_answers_file.close()
        
        # 创建临时zip文件
        temp_zip_file = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
        temp_zip_path = temp_zip_file.name
        temp_zip_file.close()
        
        # 生成题目PDF
        pdf_gen.generate_pdf(all_pages, temp_questions_path)
        
        # 生成答案PDF
        pdf_gen.generate_answer_pdf(all_pages, temp_answers_path)
        
        # 将两个PDF打包成zip
        with zipfile.ZipFile(temp_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            zipf.write(temp_questions_path, 'math_exercises_questions.pdf')
            zipf.write(temp_answers_path, 'math_exercises_answers.pdf')
        
        # 返回ZIP文件，使用自定义响应类自动清理临时文件
        response = TemporaryFileResponse(
            temp_zip_path,
            content_type='application/zip'
        )
        response['Content-Disposition'] = f'attachment; filename="math_exercises.zip"'
        
        # 注册退出时清理（备用方案）
        def cleanup():
            try:
                for path in [temp_questions_path, temp_answers_path, temp_zip_path]:
                    if os.path.exists(path):
                        os.unlink(path)
            except:
                pass
        
        atexit.register(cleanup)
        
        return response
    
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
