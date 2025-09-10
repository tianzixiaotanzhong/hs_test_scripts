import jenkins.model.*
import hudson.model.*
import groovy.json.JsonOutput
import java.net.HttpURLConnection
import java.net.URL
import javax.crypto.Mac
import javax.crypto.spec.SecretKeySpec
import java.util.Base64

/********** 可调参数 **********/
int FAIL_THRESHOLD = 5    // 连续失败阈值
boolean DRY_RUN = false    // 先试跑不禁用可设为 true，看日志效果
/*****************************/

def jenkins = Jenkins.instance
def rootUrl = jenkins.getRootUrl() ?: '(请在 Manage Jenkins → Configure System 设置 Jenkins URL)'

// 获取飞书配置的函数
def getFeishuConfig() {
    def config = [:]
    def jenkinsInstance = Jenkins.instance
    
    // 从系统环境变量读取
    config.webhook = System.getenv('FEISHU_WEBHOOK')
    config.secret = System.getenv('FEISHU_SECRET')
    
    // 如果环境变量为空，尝试从 Jenkins 全局环境变量里取
    if (!config.webhook) {
        config.webhook = jenkinsInstance.getGlobalNodeProperties()
            .getAll(hudson.slaves.EnvironmentVariablesNodeProperty.class)
            .collect { it.envVars }
            .findResult { it['FEISHU_WEBHOOK'] }
    }
    
    if (!config.secret) {
        config.secret = jenkinsInstance.getGlobalNodeProperties()
            .getAll(hudson.slaves.EnvironmentVariablesNodeProperty.class)
            .collect { it.envVars }
            .findResult { it['FEISHU_SECRET'] }
    }
    
    return config
}

// 发送飞书通知
def sendFeishu(String jobFullName, String jobUrl, Map feishuConfig, int failThreshold) {
    if (!feishuConfig.webhook) {
        println "[WARN] 未配置 FEISHU_WEBHOOK，跳过发送飞书通知。"
        return
    }

    def contentText = """⚠️ Jenkins Job 已被禁用
Job: ${jobFullName}
原因: 最近 ${failThreshold} 次构建全部失败
链接: ${jobUrl}
时间: ${new Date()}
"""

    def payload = [msg_type: "text", content: [text: contentText]]

    // 如果配置了飞书签名 secret，需要附上 timestamp & sign
    if (feishuConfig.secret) {
        long timestamp = System.currentTimeMillis() / 1000
        String stringToSign = "${timestamp}\n${feishuConfig.secret}"
        Mac mac = Mac.getInstance("HmacSHA256")
        mac.init(new SecretKeySpec(feishuConfig.secret.getBytes("UTF-8"), "HmacSHA256"))
        byte[] signData = mac.doFinal(stringToSign.getBytes("UTF-8"))
        String sign = Base64.encoder.encodeToString(signData)

        payload.timestamp = timestamp
        payload.sign = sign
    }

    try {
        def url = new URL(feishuConfig.webhook)
        def conn = url.openConnection() as HttpURLConnection
        conn.setRequestMethod("POST")
        conn.setRequestProperty("Content-Type", "application/json; charset=UTF-8")
        conn.doOutput = true
        def body = JsonOutput.toJson(payload)

        conn.outputStream.withWriter("UTF-8") { it.write(body) }
        def code = conn.responseCode
        println "飞书通知已发送: ${jobFullName}, HTTP ${code}"
    } catch (Exception e) {
        println "发送飞书通知失败: ${e.message}"
    }
}

// 获取"最近已完成"的构建列表，最多 N 条（忽略进行中的构建）
def latestCompletedBuilds(Job job, int n) {
    def list = []
    for (Run r : job.getBuilds()) {
        if (r == null) continue
        def res = r.getResult()
        if (res != null) {
            list.add(r)
            if (list.size() >= n) break
        }
    }
    return list
}

// 获取飞书配置
def feishuConfig = getFeishuConfig()

// 主逻辑：遍历所有 Job
jenkins.getAllItems(Job.class).each { Job job ->
    try {
        if (job.isDisabled()) {
            println "跳过（已禁用）: ${job.fullName}"
            return
        }

        def builds = latestCompletedBuilds(job, FAIL_THRESHOLD)

        if (builds.size() < FAIL_THRESHOLD) {
            println "跳过（构建不足 ${FAIL_THRESHOLD} 次）: ${job.fullName}"
            return
        }

        boolean allFailed = builds.every { it.getResult() == Result.FAILURE }

        if (allFailed) {
            // 检查最新构建的触发原因，判断是否由用户手动触发
            def latestBuild = job.getLastBuild()
            if (latestBuild != null && latestBuild.isBuilding()) {
                // 获取构建的触发原因
                def causes = latestBuild.getCauses()
                boolean isManuallyTriggered = false
                
                for (cause in causes) {
                    def causeClass = cause.getClass().getSimpleName()
                    def causeDesc = cause.getShortDescription()
                    
                    // 检查是否为用户手动触发
                    // UserIdCause: 用户在界面上点击构建
                    // UserCause: 用户通过API触发
                    // CLICause: 通过CLI触发
                    // RemoteCause: 远程触发
                    if (causeClass.contains("UserIdCause") || 
                        causeClass.contains("UserCause") || 
                        causeClass.contains("CLICause") ||
                        causeClass.contains("RemoteCause") ||
                        causeDesc.toLowerCase().contains("user") ||
                        causeDesc.toLowerCase().contains("manually")) {
                        isManuallyTriggered = true
                        break
                    }
                }
                
                if (isManuallyTriggered) {
                    println "跳过（有用户手动触发的构建正在运行 #${latestBuild.getNumber()}）: ${job.fullName}"
                    return
                }
            }
            
            def jobUrl = rootUrl.endsWith("/") ? (rootUrl + job.getUrl()) : (rootUrl + "/" + job.getUrl())
            if (!DRY_RUN) {
                println "⚠️ 连续失败 ${FAIL_THRESHOLD} 次，禁用 Job: ${job.fullName}"
                job.disable()
                job.save()
                sendFeishu(job.fullName, jobUrl, feishuConfig, FAIL_THRESHOLD)
            } else {
                println "[DRY_RUN] 将禁用 Job: ${job.fullName}，并发送飞书通知 → ${jobUrl}"
            }
        } else {
            int fails = builds.count { it.getResult() == Result.FAILURE }
            println "OK: ${job.fullName} 最近 ${builds.size()} 次中失败 ${fails} 次（未达到连续 ${FAIL_THRESHOLD} 次失败）"
        }
    } catch (Exception e) {
        println "处理出错: ${job.fullName} → ${e.message}"
    }
}

println "扫描完成于：${new Date()}"