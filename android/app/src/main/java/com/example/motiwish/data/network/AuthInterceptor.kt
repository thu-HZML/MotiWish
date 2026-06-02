import com.example.motiwish.data.network.TokenManager
import okhttp3.Interceptor
import okhttp3.Response

class AuthInterceptor : Interceptor {
    override fun intercept(chain: Interceptor.Chain): Response {
        val originalRequest = chain.request()
        val urlPath = originalRequest.url.encodedPath

        // 判断当前请求是否为登录或注册接口（根据你的实际路径）
        val isAuthRequest = urlPath == "/api/v1/users/auth/login/" ||
                urlPath == "/api/v1/users/auth/register/"

        val requestBuilder = originalRequest.newBuilder()

        // 只有在非登录/注册请求，并且 Token 存在时，才添加 Authorization 头
        if (!isAuthRequest) {
            val token = TokenManager.getToken()
            if (!token.isNullOrEmpty()) {
                requestBuilder.addHeader("Authorization", "Bearer $token")
            }
        }

        return chain.proceed(requestBuilder.build())
    }
}