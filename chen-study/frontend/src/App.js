import React, { useState } from 'react';
import './App.css';
import axios from 'axios';

function App() {
  const [numPages, setNumPages] = useState(2);
  const [maxValue, setMaxValue] = useState(20);
  const [difficulty, setDifficulty] = useState(50);
  const [operations, setOperations] = useState({
    addition: true,
    subtraction: true,
    multiplication: false,
    division: false,
    addition_multiplication: false,
    addition_division: false,
    subtraction_multiplication: false,
    subtraction_division: false
  });
  const [fillType, setFillType] = useState('result');
  const [previewHtml, setPreviewHtml] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleOperationChange = (op) => {
    setOperations(prev => ({
      ...prev,
      [op]: !prev[op]
    }));
  };

  const handleGeneratePreview = async () => {
    // 检查至少选择一种运算
    const selectedOps = Object.keys(operations).filter(op => operations[op]);
    if (selectedOps.length === 0) {
      setError('请至少选择一种运算类型');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await axios.post('http://localhost:8000/api/generate-preview/', {
        num_pages: numPages,
        max_value: maxValue,
        operations: selectedOps,
        fill_type: fillType,
        difficulty: difficulty
      });

      setPreviewHtml(response.data.html);
    } catch (err) {
      setError(err.response?.data?.error || '生成预览失败，请检查后端服务是否运行');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleDownloadPDF = async () => {
    const selectedOps = Object.keys(operations).filter(op => operations[op]);
    if (selectedOps.length === 0) {
      setError('请至少选择一种运算类型');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await axios.post(
        'http://localhost:8000/api/generate-pdf/',
        {
          num_pages: numPages,
          max_value: maxValue,
          operations: selectedOps,
          fill_type: fillType,
          difficulty: difficulty
        },
        {
          responseType: 'blob'
        }
      );

      // 创建下载链接（现在是zip文件，包含题目和答案两个PDF）
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', 'math_exercises.zip');
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setError(err.response?.data?.error || '生成PDF失败，请检查后端服务是否运行');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="App">
      <div className="container">
        <header className="header">
          <h1>小学数学练习题生成器</h1>
        </header>

        <div className="form-container">
          <div className="form-group">
            <label>页数 (N):</label>
            <input
              type="number"
              min="1"
              max="50"
              value={numPages}
              onChange={(e) => setNumPages(parseInt(e.target.value) || 1)}
            />
          </div>

          <div className="form-group">
            <label>最大数值 (M):</label>
            <input
              type="number"
              min="1"
              max="100"
              value={maxValue}
              onChange={(e) => setMaxValue(parseInt(e.target.value) || 1)}
            />
          </div>

          <div className="form-group">
            <label>难度值: {difficulty}</label>
            <input
              type="range"
              min="1"
              max="100"
              value={difficulty}
              onChange={(e) => setDifficulty(parseInt(e.target.value))}
              className="slider"
            />
            <div className="slider-labels">
              <span>简单 (1)</span>
              <span>中等 (50)</span>
              <span>困难 (100)</span>
            </div>
          </div>

          <div className="form-group">
            <label>运算类型:</label>
            <div className="checkbox-group">
              <label>
                <input
                  type="checkbox"
                  checked={operations.addition}
                  onChange={() => handleOperationChange('addition')}
                />
                加法
              </label>
              <label>
                <input
                  type="checkbox"
                  checked={operations.subtraction}
                  onChange={() => handleOperationChange('subtraction')}
                />
                减法
              </label>
              <label>
                <input
                  type="checkbox"
                  checked={operations.multiplication}
                  onChange={() => handleOperationChange('multiplication')}
                />
                乘法（表内）
              </label>
              <label>
                <input
                  type="checkbox"
                  checked={operations.division}
                  onChange={() => handleOperationChange('division')}
                />
                除法（表内）
              </label>
            </div>
            <div style={{ marginTop: '15px', paddingTop: '15px', borderTop: '1px solid #e0e0e0' }}>
              <label style={{ fontWeight: '600', color: '#333', display: 'block', marginBottom: '10px' }}>混合运算:</label>
              <div className="checkbox-group">
              <label>
                <input
                  type="checkbox"
                  checked={operations.addition_multiplication}
                  onChange={() => handleOperationChange('addition_multiplication')}
                />
                加乘（先乘后加）
              </label>
              <label>
                <input
                  type="checkbox"
                  checked={operations.addition_division}
                  onChange={() => handleOperationChange('addition_division')}
                />
                加除（先除后加）
              </label>
              <label>
                <input
                  type="checkbox"
                  checked={operations.subtraction_multiplication}
                  onChange={() => handleOperationChange('subtraction_multiplication')}
                />
                减乘（先乘后减）
              </label>
              <label>
                <input
                  type="checkbox"
                  checked={operations.subtraction_division}
                  onChange={() => handleOperationChange('subtraction_division')}
                />
                减除（先除后减）
              </label>
              </div>
            </div>
          </div>

          <div className="form-group">
            <label>题目类型:</label>
            <div className="radio-group">
              <label>
                <input
                  type="radio"
                  value="result"
                  checked={fillType === 'result'}
                  onChange={(e) => setFillType(e.target.value)}
                />
                填写结果
              </label>
              <label>
                <input
                  type="radio"
                  value="operand"
                  checked={fillType === 'operand'}
                  onChange={(e) => setFillType(e.target.value)}
                />
                填写中间值（加数、减数、乘数、除数等）
              </label>
            </div>
          </div>

          {error && <div className="error-message">{error}</div>}

          <div className="button-group">
            <button
              onClick={handleGeneratePreview}
              disabled={loading}
              className="btn btn-primary"
            >
              {loading ? '生成中...' : '生成预览'}
            </button>
            <button
              onClick={handleDownloadPDF}
              disabled={loading || !previewHtml}
              className="btn btn-secondary"
            >
              {loading ? '生成中...' : '下载PDF（题目+答案）'}
            </button>
          </div>
        </div>

        {previewHtml && (
          <div className="preview-container">
            <h2>预览</h2>
            <div
              className="preview-content"
              dangerouslySetInnerHTML={{ __html: previewHtml }}
            />
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
