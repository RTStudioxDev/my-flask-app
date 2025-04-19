from flask import Flask, render_template, request, redirect, url_for, flash, send_file, abort
from datetime import datetime
from pymongo import MongoClient
from bson import ObjectId
import os
from dotenv import load_dotenv
from openpyxl import Workbook
from openpyxl.utils import get_column_letter
from io import BytesIO
from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
from pymongo import TEXT
from math import ceil

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')

client = MongoClient(os.getenv('MONGODB_URI'))
db = client['finance_web_app']


with app.app_context():
    db.transactions.create_index([('agent', TEXT)])

@app.context_processor
def inject_datetime():
    return {'datetime': datetime}

@app.template_filter('number_format')
def number_format(value, precision=2):
    try:
        return f"{float(value):,.{precision}f}"
    except (ValueError, TypeError):
        return value

@app.route('/')
def index():
    agents = list(db.agents.find())
    return render_template('index.html', agents=agents)

@app.route('/submit', methods=['POST'])
def submit_transaction():
    try:
        transaction_data = {
            'agent': request.form.get('agent'),
            'date': datetime.strptime(request.form.get('date'), '%Y-%m-%d'),
            'new_members': int(request.form.get('new_members', 0)),
            'first_deposit': float(request.form.get('first_deposit', 0)),
            'all_deposit': float(request.form.get('all_deposit', 0)),
            'used': int(request.form.get('used', 0)),
            'db': float(request.form.get('db', 0)),
            'kbank_deposit': float(request.form.get('kbank_deposit', 0)),
            'kbiz_deposit': float(request.form.get('kbiz_deposit', 0)),
            'scb1_deposit': float(request.form.get('scb1_deposit', 0)),
            'scb2_deposit': float(request.form.get('scb2_deposit', 0)),
            'true_deposit': float(request.form.get('true_deposit', 0)),
            'mobile_deposit': float(request.form.get('mobile_deposit', 0)),
            'kbank_withdrawal': float(request.form.get('kbank_withdrawal', 0)),
            'kbiz_withdrawal': float(request.form.get('kbiz_withdrawal', 0)),
            'scb1_withdrawal': float(request.form.get('scb1_withdrawal', 0)),
            'scb2_withdrawal': float(request.form.get('scb2_withdrawal', 0)),
            'true_withdrawal': float(request.form.get('true_withdrawal', 0)),
            'profit_thb': float(request.form.get('profit_thb', 0)),
            'profit_usdt': float(request.form.get('profit_usdt', 0)),
            'transfer': float(request.form.get('transfer', 0)),
            'bonus': float(request.form.get('bonus', 0)),
            'commission': float(request.form.get('commission', 0)),
            'admin_approved': int(request.form.get('admin_approved', 0)),
            'created_at': datetime.now()
        }

        if not transaction_data['agent']:
            flash('กรุณาเลือก Agent', 'danger')
            return redirect(url_for('index'))

        db.transactions.insert_one(transaction_data)
        flash('บันทึกข้อมูลสำเร็จ', 'success')
        return redirect(url_for('show_history'))

    except Exception as e:
        flash(f'เกิดข้อผิดพลาด: {str(e)}', 'danger')
        return redirect(url_for('index'))

@app.route('/history')
def show_history():
    # กำหนดค่าเริ่มต้น
    query = {}
    page = request.args.get('page', 1, type=int)
    per_page = 31

    # ดึงค่าตัวกรองจาก URL Parameters
    selected_agent = request.args.get('agent', '')
    selected_month = request.args.get('month', '')
    selected_year = request.args.get('year', '')
    

    # สร้าง query สำหรับ MongoDB
    query = {}
    
    # กรองตาม Agent
    if selected_agent:
        query['agent'] = selected_agent
    
    # กรองตามเดือน/ปี
    if selected_month and selected_year:
        try:
            start_date = datetime(int(selected_year), int(selected_month), 1)
            end_month = int(selected_month) + 1 if int(selected_month) != 12 else 1
            end_year = int(selected_year) if int(selected_month) != 12 else int(selected_year) + 1
            end_date = datetime(end_year, end_month, 1)
            query['date'] = {'$gte': start_date, '$lt': end_date}
        except ValueError:
            flash('รูปแบบเดือน/ปีไม่ถูกต้อง', 'danger')

    # เพิ่มการดึงรายชื่อ Agent ที่ไม่ซ้ำกัน
    unique_agents = db.transactions.distinct('agent')

    # ดึงข้อมูลและนับจำนวน (แก้ไขตรงนี้)
    transactions_cursor = db.transactions.find(query).sort('date', -1)
    total = db.transactions.count_documents(query)
    transactions_list = list(transactions_cursor.skip((page - 1) * per_page).limit(per_page))

    # คำนวณยอดรวม
    total_deposit = sum(
        t.get('kbank_deposit', 0) + 
        t.get('kbiz_deposit', 0) + 
        t.get('scb1_deposit', 0) + 
        t.get('scb2_deposit', 0) + 
        t.get('true_deposit', 0) 
        for t in transactions_list
    )

    total_withdrawal = sum(
        t.get('kbank_withdrawal', 0) + 
        t.get('kbiz_withdrawal', 0) + 
        t.get('scb1_withdrawal', 0) + 
        t.get('scb2_withdrawal', 0) + 
        t.get('true_withdrawal', 0) 
        for t in transactions_list
    )

    total_commission = sum(t.get('commission', 0) for t in transactions_list)
    total_bonus = sum(t.get('bonus', 0) for t in transactions_list)

    # คำนวณยอดดุล
    balance = total_deposit - (total_withdrawal + total_commission + total_bonus)

    # เพิ่มการดึงค่า selected_agent จาก query parameters
    selected_agent = request.args.get('agent')
    if selected_agent:
        query['agent'] = selected_agent

    # สร้าง Pagination object
    class Pagination:
        def __init__(self, page, per_page, total, items):
            self.page = page
            self.per_page = per_page
            self.total = total
            self.items = items  # เก็บข้อมูลรายการ
            self.pages = (total // per_page) + (1 if total % per_page > 0 else 0)
            self.has_prev = page > 1
            self.has_next = page < self.pages
            self.prev_num = page - 1 if self.has_prev else None
            self.next_num = page + 1 if self.has_next else None

        def iter_pages(self, left_edge=2, left_current=2, right_current=5, right_edge=2):
            last = 0
            for num in range(1, self.pages + 1):
                if (num <= left_edge or 
                    (num > self.page - left_current - 1 and num < self.page + right_current) or 
                    num > self.pages - right_edge):
                    if last + 1 != num:
                        yield None
                    yield num
                    last = num

    # สร้าง Pagination object
    pagination = Pagination(
        page=page,
        per_page=per_page,
        total=total,
        items=transactions_list  # ใช้รายการข้อมูลที่ดึงมา
    )

    # ดึงเดือน/ปีที่มีข้อมูล
    months_years = list(db.transactions.aggregate([
        {"$group": {
            "_id": {
                "year": {"$year": "$date"},
                "month": {"$month": "$date"}
            }
        }},
        {"$sort": {"_id.year": -1, "_id.month": -1}}
    ]))
    
    return render_template('history.html',
                        unique_agents=unique_agents,
                        selected_agent=selected_agent,
                        transactions=pagination,
                        total_deposit=total_deposit,
                        total_withdrawal=total_withdrawal,
                        total_commission=total_commission,
                        total_bonus=total_bonus,
                        balance=balance,
                        months_years=months_years,
                        selected_month=selected_month,
                        selected_year=selected_year)

@app.route('/agents', methods=['GET', 'POST'])
def manage_agents():
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'add':
            db.agents.insert_one({
                'name': request.form.get('name'),
                'created_at': datetime.now()
            })
            flash('เพิ่ม Agent สำเร็จ', 'success')
            
        elif action == 'delete':
            try:
                agent_id = ObjectId(request.form.get('agent_id'))
                result = db.agents.delete_one({'_id': agent_id})
                if result.deleted_count > 0:
                    flash('ลบ Agent สำเร็จ', 'success')
                else:
                    flash('ไม่พบ Agent ที่ต้องการลบ', 'danger')
            except Exception as e:
                flash(f'เกิดข้อผิดพลาด: {str(e)}', 'danger')
        
        return redirect(url_for('manage_agents'))
    
    agents = list(db.agents.find())
    return render_template('agents.html', agents=agents)

@app.route('/delete-transaction/<transaction_id>', methods=['POST'])
def delete_transaction(transaction_id):
    try:
        obj_id = ObjectId(transaction_id)
        result = db.transactions.delete_one({'_id': obj_id})
        
        if result.deleted_count > 0:
            flash('ลบรายการสำเร็จ', 'success')
        else:
            flash('ไม่พบรายการที่ต้องการลบ', 'danger')
            
    except Exception as e:
        flash(f'เกิดข้อผิดพลาด: {str(e)}', 'danger')
    
    return redirect(url_for('show_history'))

@app.route('/export/<transaction_id>')
def export_excel(transaction_id):
    try:
        transaction = db.transactions.find_one({'_id': ObjectId(transaction_id)})
        
        if not transaction:
            flash('ไม่พบรายการนี้ในระบบ', 'danger')
            return redirect(url_for('show_history'))

        # ตรวจสอบและตั้งค่าเริ่มต้นสำหรับฟิลด์ที่อาจไม่มี
        transaction.setdefault('first_deposit', 0)
        transaction.setdefault('mobile_deposit', 0)
        transaction.setdefault('commission', 0)
        transaction.setdefault('bonus', 0)
        transaction.setdefault('transfer', 0)

        # สร้างไฟล์ Excel
        wb = Workbook()
        ws = wb.active
        ws.title = "สรุปยอดปิดกะ"

        # สไตล์และรูปแบบ
        header_fill = PatternFill(start_color='FF9900', fill_type='solid')
        yellow_fill = PatternFill(start_color='FFFF00', fill_type='solid')
        green_fill = PatternFill(start_color='D9EAD3', fill_type='solid')
        red_fill = PatternFill(start_color='F4CCCC', fill_type='solid')
        gray_fill = PatternFill(start_color='F3F3F3', fill_type='solid')
        blue_fill = PatternFill(start_color='c9daf8', fill_type='solid')
        border = Border(left=Side(style='thin'), right=Side(style='thin'),
                        top=Side(style='thin'), bottom=Side(style='thin'))

        # ส่วนหัวหลัก
        ws.merge_cells('A1:N1')
        ws['A1'] = f"สรุปยอดปิดกะ {transaction['agent']} วันที่ {transaction['date'].strftime('%d/%m/%Y')}"
        ws['A1'].font = Font(name="K2D", bold=True, size=15)
        ws['A1'].fill = header_fill
        ws['A1'].alignment = Alignment(horizontal='center')

        # ส่วนหัวตาราง
        headers = [
            "วัน", "ฝาก", "เติมมือ", "ถอน", "ถอนมือ", 
            "ขาด/เกิน", "กำไร", "สมัคร", "เติมจริง", 
            "ไม่เติม", "ฝากแรก", "แอคทีฟ", "โบนัส", "ค่าคอม"
        ]
        
        for col_num, header in enumerate(headers, 1):
            cell = ws.cell(row=2, column=col_num, value=header)
            cell.fill = yellow_fill
            cell.border = border

        # คำนวณค่าต่างๆ
        total_deposit = sum([
            transaction.get('kbank_deposit', 0),
            transaction.get('kbiz_deposit', 0),
            transaction.get('scb1_deposit', 0),
            transaction.get('scb2_deposit', 0),
            transaction.get('true_deposit', 0)
        ])
        
        total_withdrawal = sum([
            transaction.get('kbank_withdrawal', 0),
            transaction.get('kbiz_withdrawal', 0),
            transaction.get('scb1_withdrawal', 0),
            transaction.get('scb2_withdrawal', 0),
            transaction.get('true_withdrawal', 0)
        ])
        
        atm_balance = total_deposit - (total_withdrawal + transaction.get('commission', 0))
        shortfall = transaction.get('transfer', 0) - atm_balance

        # ใส่ข้อมูล
        data_row = [
            transaction['date'].strftime('%d/%m/%Y'),
            total_deposit,
            transaction.get('mobile_deposit', 0),
            total_withdrawal,
            # total_withdrawal, #ใส่สูตร(E3)
            shortfall,
            # total_deposit - (total_withdrawal + transaction.get('commission', 0)) + shortfall, #ใส่สูตร(G3)
            transaction.get('new_members', 0),
            transaction.get('first_deposit', 0),
            # transaction.get('new_members', 0) - transaction.get('first_deposit', 0), #ใส่สูตร(J3)
            transaction.get('all_deposit', 0),
            transaction.get('used', 0),
            transaction.get('bonus', 0),
            transaction.get('commission', 0)
        ]        

        for col_num, value in enumerate(data_row, 1):
            cell = ws.cell(row=3, column=col_num)
            
            # กำหนดสูตรและค่า
            if col_num == 5:    # E3
                cell.value = '=SUM(D3)'
                cell.number_format = '#,##0.00'
            elif col_num == 7: # G3
                cell.value = '=SUM(B3-(D3+N3)+F3)'
            elif col_num == 10: # J3
                cell.value = '=SUM(H3-I3)'
            else:
                cell.value = value  # ค่าปกติสำหรับคอลัมน์อื่นๆ
            
            # กำหนดสไตล์
            cell.border = border
            cell.alignment = Alignment(horizontal='center')
            
            if col_num == 4:    # คอลัมน์ D
                cell.fill = red_fill
                cell.number_format = '#,##0.00'
            elif col_num == 13: # คอลัมน์ M
                cell.fill = blue_fill
                cell.number_format = '#,##0.00'
            elif col_num in [6,7]: # คอลัมน์ F และ G
                cell.fill = green_fill if (value >= 0 if col_num != 5 else cell.value >= 0) else red_fill
                cell.number_format = '#,##0.00'
            elif col_num in [2,3,4,5]:
                cell.number_format = '#,##0.00'
            else:
                cell.fill = gray_fill
                cell.number_format = '#,##0'

        # ปรับความกว้างคอลัมน์
        column_widths = [15, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12]
        for i, width in enumerate(column_widths, 1):
            ws.column_dimensions[get_column_letter(i)].width = width

        for col in range(1, 15):
            cell = ws.cell(row=2, column=col)
            cell.font = Font(name="Arial", bold=False, size=8)
            cell.fill = yellow_fill
            cell.alignment = Alignment(horizontal='center')

        # ส่งไฟล์กลับ
        buffer = BytesIO()
        wb.save(buffer)
        buffer.seek(0)
        
        return send_file(
            buffer,
            as_attachment=True,
            download_name=f"สรุปยอด_{transaction['agent']}_{transaction['date'].strftime('%Y%m%d')}.xlsx",
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

    except Exception as e:
        flash(f'เกิดข้อผิดพลาดในการส่งออกไฟล์: {str(e)}', 'danger')
        return redirect(url_for('show_history'))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)