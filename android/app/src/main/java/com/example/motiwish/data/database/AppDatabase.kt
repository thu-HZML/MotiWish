package com.example.motiwish.data.database

import androidx.room.Database
import androidx.room.Room
import androidx.room.RoomDatabase
import androidx.room.TypeConverters
import android.content.Context
import androidx.sqlite.db.SupportSQLiteDatabase // 注意这里新增了导包
import com.example.motiwish.data.model.*

@Database(
    entities = [
        DailyMetric::class,
        PeriodicTask::class,
        OneShotTask::class,
        Transaction::class,
        Wish::class,
        CurrencyBalance::class,
        PeriodicTaskCompletion::class
    ],
    version = 1,
    exportSchema = false
)
@TypeConverters(Converters::class)
abstract class AppDatabase : RoomDatabase() {
    abstract fun taskDao(): TaskDao
    abstract fun currencyDao(): CurrencyDao
    abstract fun wishDao(): WishDao

    companion object {
        @Volatile
        private var INSTANCE: AppDatabase? = null

        fun getDatabase(context: Context): AppDatabase {
            return INSTANCE ?: synchronized(this) {
                val instance = Room.databaseBuilder(
                    context.applicationContext,
                    AppDatabase::class.java,
                    "self_management_db"
                )
                    // 【核心修改】：添加数据库回调，在首次创建时插入初始货币记录
                    .addCallback(object : RoomDatabase.Callback() {
                        override fun onCreate(db: SupportSQLiteDatabase) {
                            super.onCreate(db)
                            // 插入 id=1 的初始余额，默认值均为 0
                            db.execSQL("INSERT INTO currency_balance (id, primaryCurrency, secondaryCurrency) VALUES (1, 100, 100)")
                        }
                    })
                    .build()

                INSTANCE = instance
                instance
            }
        }
    }
}