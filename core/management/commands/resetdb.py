# myapp/management/commands/resetdb.py
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.conf import settings
import os
import subprocess
from datetime import datetime

class Command(BaseCommand):
    help = 'يقوم بإعادة تعيين قاعدة البيانات بشكل كامل (فورمات)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--no-backup',
            action='store_true',
            help='تخطي عمل نسخة احتياطية',
        )
        parser.add_argument(
            '--no-input',
            action='store_true',
            help='تخطي التأكيد التلقائي',
        )

    def handle(self, *args, **options):
        # التحقق من أننا في وضع التطوير فقط
        if not settings.DEBUG:
            raise CommandError('هذا الأمر مسموح به فقط في وضع التطوير (DEBUG=True)')

        # طلب التأكيد من المستخدم
        if not options['no_input']:
            confirm = input("""⛔️ تحذير: هذا سيمسح جميع البيانات في قاعدة البيانات!
هل أنت متأكد أنك تريد المتابعة؟ (نعم/لا): """)
            if confirm.lower() not in ['نعم', 'yes', 'y', 'ن']:
                self.stdout.write(self.style.WARNING('تم إلغاء العملية.'))
                return

        # عمل نسخة احتياطية إذا طلب
        if not options['no_backup']:
            self.create_backup()

        # إعادة تعيين قاعدة البيانات
        self.reset_database()

        # تشغيل migrations
        self.run_migrations()

        # إنشاء مستخدم superuser افتراضي
        self.create_superuser()

        self.stdout.write(self.style.SUCCESS('✅ تم إعادة تعيين قاعدة البيانات بنجاح!'))

    def create_backup(self):
        """إنشاء نسخة احتياطية من قاعدة البيانات"""
        self.stdout.write('إنشاء نسخة احتياطية...')
        
        # إنشاء مجلد النسخ الاحتياطية إذا لم يكن موجوداً
        backup_dir = os.path.join(settings.BASE_DIR, 'backups')
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
        
        # اسم ملف النسخة الاحتياطية
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = os.path.join(backup_dir, f'db_backup_{timestamp}.sql')
        
        # نسخ احتياطي حسب نوع قاعدة البيانات
        db_engine = settings.DATABASES['default']['ENGINE']
        
        try:
            if 'sqlite3' in db_engine:
                import shutil
                db_path = settings.DATABASES['default']['NAME']
                if os.path.exists(db_path):
                    shutil.copy2(db_path, backup_file)
                else:
                    self.stdout.write(self.style.WARNING('⚠️  قاعدة البيانات SQLite غير موجودة، سيتم إنشاؤها لاحقاً'))
                
            elif 'postgresql' in db_engine:
                # تحتاج إلى تثبيت pg_dump لهذا
                db = settings.DATABASES['default']
                env = os.environ.copy()
                env['PGPASSWORD'] = db['PASSWORD']
                
                cmd = [
                    'pg_dump', 
                    '-h', db['HOST'],
                    '-U', db['USER'],
                    '-d', db['NAME'],
                    '-f', backup_file
                ]
                
                subprocess.run(cmd, env=env, check=True)
                
            elif 'mysql' in db_engine:
                db = settings.DATABASES['default']
                env = os.environ.copy()
                env['MYSQL_PWD'] = db['PASSWORD']
                
                cmd = [
                    'mysqldump',
                    '-h', db['HOST'],
                    '-u', db['USER'],
                    db['NAME']
                ]
                
                with open(backup_file, 'w') as f:
                    subprocess.run(cmd, env=env, stdout=f, check=True)
                
            self.stdout.write(self.style.SUCCESS(f'✅ تم إنشاء نسخة احتياطية في: {backup_file}'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ فشل في إنشاء نسخة احتياطية: {e}'))
            if not options.get('no_input', False):
                confirm = input("هل تريد المتابعة بدون نسخة احتياطية؟ (نعم/لا): ")
                if confirm.lower() not in ['نعم', 'yes', 'y', 'ن']:
                    raise CommandError('تم إلغاء العملية بسبب فشل النسخ الاحتياطي')
            else:
                self.stdout.write(self.style.WARNING('⚠️  المتابعة بدون نسخة احتياطية'))

def reset_database(self):
        """إعادة تعيين قاعدة البيانات"""
        self.stdout.write('جاري إعادة تعيين قاعدة البيانات...')
        
        db_engine = settings.DATABASES['default']['ENGINE']
        
        try:
            if 'sqlite3' in db_engine:
                db_path = settings.DATABASES['default']['NAME']
                if os.path.exists(db_path):
                    os.remove(db_path)
                    self.stdout.write(self.style.SUCCESS('✅ تم حذف قاعدة البيانات SQLite'))
                else:
                    self.stdout.write(self.style.WARNING('⚠️  قاعدة البيانات SQLite غير موجودة، سيتم إنشاؤها لاحقاً'))
                
            elif 'postgresql' in db_engine:
                import psycopg2
                from psycopg2 import sql
                
                db = settings.DATABASES['default']
                
                # الاتصال بقاعدة بيانات postgres الافتراضية لإنشاء قاعدة بيانات جديدة
                conn = psycopg2.connect(
                    host=db['HOST'],
                    user=db['USER'],
                    password=db['PASSWORD'],
                    database='postgres'
                )
                conn.autocommit = True
                cursor = conn.cursor()
                
                # إنهاء جميع الاتصالات الحالية
                cursor.execute("""
                    SELECT pg_terminate_backend(pg_stat_activity.pid)
                    FROM pg_stat_activity
                    WHERE pg_stat_activity.datname = %s
                    AND pid <> pg_backend_pid();
                """, [db['NAME']])
                
                # حذف وإعادة إنشاء قاعدة البيانات
                cursor.execute(sql.SQL("DROP DATABASE IF EXISTS {}").format(
                    sql.Identifier(db['NAME'])
                ))
                
                cursor.execute(sql.SQL("CREATE DATABASE {}").format(
                    sql.Identifier(db['NAME'])
                ))
                
                cursor.close()
                conn.close()
                self.stdout.write(self.style.SUCCESS('✅ تم إعادة إنشاء قاعدة البيانات PostgreSQL'))
                
            elif 'mysql' in db_engine:
                import pymysql
                db = settings.DATABASES['default']
                
                # الاتصال بـ MySQL لإنشاء قاعدة بيانات جديدة
                conn = pymysql.connect(
                    host=db['HOST'],
                    user=db['USER'],
                    password=db['PASSWORD']
                )
                cursor = conn.cursor()
                
                cursor.execute(f'DROP DATABASE IF EXISTS {db["NAME"]}')
                cursor.execute(f'CREATE DATABASE {db["NAME"]} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci')
                
                cursor.close()
                conn.close()
                self.stdout.write(self.style.SUCCESS('✅ تم إعادة إنشاء قاعدة البيانات MySQL'))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ فشل في إعادة تعيين قاعدة البيانات: {e}'))
            raise CommandError('فشل في إعادة تعيين قاعدة البيانات')

def run_migrations(self):
        """تشغيل migrations"""
        self.stdout.write('جاري تطبيق migrations...')
        
        try:
            # إعادة الاتصال بقاعدة البيانات بعد إعادة الإنشاء
            from django.db import connections
            connections.close_all()
            
            # تطبيق migrations
            from django.core.management import execute_from_command_line
            execute_from_command_line(['manage.py', 'migrate'])
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ فشل في تطبيق migrations: {e}'))
            raise CommandError('فشل في تطبيق migrations')

def create_superuser(self):
        """إنشاء مستخدم افتراضي إذا لم يوجد"""
        self.stdout.write('جاري إنشاء مستخدم افتراضي...')
        
        try:
            # إعادة الاتصال بقاعدة البيانات
            from django.db import connections
            connections.close_all()
            
            from django.contrib.auth import get_user_model
            User = get_user_model()
            
            # نحتاج إلى استيراد النماذج بعد إعادة إنشاء قاعدة البيانات
            from django.apps import apps
            apps.get_models()
            
            if not User.objects.filter(username='admin').exists():
                User.objects.create_superuser('admin', 'admin@example.com', 'admin')
                self.stdout.write(self.style.SUCCESS('✅ تم إنشاء المستخدم الافتراضي (admin/admin)'))
            else:
                self.stdout.write(self.style.WARNING('⚠️  المستخدم admin موجود مسبقاً'))
                
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'⚠️  فشل في إنشاء المستخدم الافتراضي: {e}'))
            self.stdout.write(self.style.WARNING('يمكنك إنشاء مستخدم يدوياً باستخدام: python manage.py createsuperuser'))